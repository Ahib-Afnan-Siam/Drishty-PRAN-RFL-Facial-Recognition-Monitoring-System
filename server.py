# server.py

import os
os.environ['OPENCV_LOG_LEVEL'] = 'OFF'

import cv2
import yaml
import numpy as np
import threading
import time
import base64
import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict
from collections import deque
from sklearn.preprocessing import normalize
from datetime import datetime
import faiss

from logger_config import system_logger, registration_logger, detection_logger, recognition_logger
from tracker import CentroidTracker
from quality_checker import QualityChecker
from database import Database
# Add imports for new models
from yolo_detector import YOLOv8FaceDetector
from mobilefacenet_recognizer import MobileFaceNetRecognizer

# Try to import DeepSORT
try:
    from deep_sort_pytorch.deep_sort import DeepSort
    from deep_sort_pytorch.utils.parser import get_config
    DEEPSORT_AVAILABLE = True
except ImportError:
    DEEPSORT_AVAILABLE = False
    system_logger.warning("DeepSORT not available, using CentroidTracker instead")

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

class RegistrationPayload(BaseModel):
    employee_id: int; name: str; department: str; role: str
    
# --- NEW: Pydantic model for the /register endpoint ---
class NewUserPayload(BaseModel):
    metadata: RegistrationPayload
    embedding: List[float] = Field(..., min_items=512, max_items=512)

class FrameGrabber(threading.Thread):
    def __init__(self, src, cam_id):
        super().__init__()
        self.daemon = True
        self.src = src
        self.cam_id = cam_id
        
        # Handle integer camera indices (e.g., 0 for default webcam)
        capture_src = src
        if isinstance(src, str) and src.isdigit():
            capture_src = int(src)
        elif isinstance(src, str) and (src.startswith('http') or src.startswith('rtsp')):
            # Keep string URLs as they are
            pass
        
        self.stream = cv2.VideoCapture(capture_src)
        if not self.stream.isOpened():
            system_logger.error(f"[{self.cam_id}] Cannot open video stream at {capture_src}")
            raise IOError(f"Cannot open video stream at {capture_src}")
        self.grabbed, self.frame = self.stream.read()
        self.stopped = threading.Event()

    def run(self):
        while not self.stopped.is_set():
            if not self.grabbed:
                system_logger.warning(f"[{self.cam_id}] Frame source lost. Attempting to reconnect...")
                self.stream.release()
                while not self.stopped.is_set():
                    # Handle integer camera indices (e.g., 0 for default webcam)
                    capture_src = self.src
                    if isinstance(self.src, str) and self.src.isdigit():
                        capture_src = int(self.src)
                    elif isinstance(self.src, str) and (self.src.startswith('http') or self.src.startswith('rtsp')):
                        # Keep string URLs as they are
                        pass
                    
                    self.stream = cv2.VideoCapture(capture_src)
                    if self.stream.isOpened():
                        self.grabbed, self.frame = self.stream.read()
                        if self.grabbed:
                            system_logger.success(f"[{self.cam_id}] Reconnected to frame source.")
                            break
                    system_logger.error(f"[{self.cam_id}] Reconnect failed. Retry in 5s...")
                    time.sleep(5)
            self.grabbed, self.frame = self.stream.read()
        if self.stream.isOpened():
            self.stream.release()

    def read(self):
        return self.frame

    def stop(self):
        self.stopped.set()

class RecognitionEngine:
    """Shared engine: FAISS index + metadata + DB + registration authority."""
    def __init__(self, config, db, initial_embeddings, initial_metadata):
        self.config = config
        self.db = db
        self.results_lock = threading.Lock()
        self.faiss_index = None
        self.metadata_cache = initial_metadata or []
        self.build_faiss_index(initial_embeddings)

    def build_faiss_index(self, embeddings):
        with self.results_lock:
            if embeddings is not None and hasattr(embeddings, "shape") and embeddings.shape[0] > 0:
                dimension = embeddings.shape[1]
                self.faiss_index = faiss.IndexFlatIP(dimension)
                self.faiss_index.add(embeddings.astype(np.float32))
                system_logger.info(f"In-memory FAISS index built with {embeddings.shape[0]} users.")
            else:
                self.faiss_index = None
                system_logger.warning("No users found. FAISS index is empty.")

    def register_new_user(self, payload: NewUserPayload):
        metadata = payload.metadata.dict()
        embedding = np.array(payload.embedding, dtype=np.float32)

        # 1) Persist to DB first
        success = self.db.add_user(metadata, embedding)
        if not success:
            registration_logger.error(f"Failed DB write for user {metadata['name']}.")
            return False, "Database write failed"

        # 2) Update shared in-memory index/cache
        with self.results_lock:
            emb_to_add = embedding.reshape(1, -1)
            if self.faiss_index is None:
                self.build_faiss_index(emb_to_add)
            else:
                self.faiss_index.add(emb_to_add)
            self.metadata_cache.append(metadata)
            system_logger.info(f"Added {metadata['name']} to FAISS. Total users: {len(self.metadata_cache)}")

        registration_logger.success(f"REGISTERED VIA API - ID: {metadata['employee_id']}, Name: {metadata['name']}")
        return True, f"Successfully registered {metadata['name']}"

    def search(self, avg_embedding: np.ndarray):
        """Return (info, similarity) for the top match or (None, None)."""
        with self.results_lock:
            if self.faiss_index is None or self.faiss_index.ntotal == 0:
                return None, None
            # Ensure the embedding is in the right format
            if len(avg_embedding.shape) == 1:
                avg_embedding = avg_embedding.reshape(1, -1)
            distances, indices = self.faiss_index.search(avg_embedding.astype(np.float32), 1)
            if indices.size > 0 and indices[0][0] != -1:
                top_idx, sim = indices[0][0], distances[0][0]
                return self.metadata_cache[top_idx], sim
            return None, None
    
    def recognize_face(self, embedding):
        """Recognize a face embedding and return (employee_id, confidence)"""
        # Log embedding dimension for debugging
        system_logger.debug(f"RecognitionEngine received embedding with shape: {embedding.shape}")
        if hasattr(self, 'faiss_index') and self.faiss_index is not None:
            system_logger.debug(f"FAISS index dimension: {self.faiss_index.d}")
            
            # Handle dimension mismatch between input embedding and FAISS index
            if len(embedding.shape) == 1:
                embedding = embedding.reshape(1, -1)
            
            # If dimensions don't match, we can't perform recognition
            if embedding.shape[1] != self.faiss_index.d:
                system_logger.error(f"Dimension mismatch: input embedding has {embedding.shape[1]} dimensions, but FAISS index expects {self.faiss_index.d} dimensions")
                return None, 0.0
        
        info, similarity = self.search(embedding)
        if info is not None:
            return info['employee_id'], similarity
        return None, 0.0

class FrameProcessor(threading.Thread):
    """Handles frame processing with adaptive frame skipping for real-time performance."""
    
    def __init__(self, config):
        super().__init__()
        self.daemon = True
        self.config = config
        self.frame_count = 0
        self.cam_id = config.get('camera_id', 'CAMERA')
        self.stopped = threading.Event()
        self.log_cooldown = 5  # seconds
        
        # Adaptive frame skipping variables
        self.processing_times = deque(maxlen=30)  # Last 30 processing times
        self.target_fps = config.get('fps_target', 30)  # Target FPS from config
        self.min_fps = config.get('min_fps', 5)  # Minimum acceptable FPS
        self.max_skip_ratio = config.get('max_frame_skip_ratio', 0.8)  # Max 80% frame skip
        self.adaptive_skip_enabled = config.get('adaptive_frame_skipping', True)
        
        # Current frame skip settings
        self.current_skip_interval = 1  # Process every Nth frame
        self.last_processing_time = 0
        self.frame_skip_counter = 0
        
        # Detection interval for YOLOv8 optimization (detect every N frames)
        self.detection_interval = config.get('yolo_detection_interval', 10)
        
        # Store last detections for tracking
        self.last_detections = []

    def run(self):
        while not self.stopped.is_set():
            frame = self.grabber.read()
            if frame is None:
                time.sleep(0.01)
                continue

            # Adaptive frame skipping
            start_time = time.time()
            
            if self._should_skip_frame():
                self.frame_count += 1
                self.frame_skip_counter += 1
                continue

            # Reset skip counter when processing a frame
            self.frame_skip_counter = 0
            
            if self.mode == "RECOGNITION":
                self._process_recognition_frame(frame)
            elif self.mode == "REGISTRATION":
                self._process_registration_frame(frame)
            
            # Record processing time for adaptive skipping
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            self.last_processing_time = processing_time
            
            self.frame_count += 1
            time.sleep(0.005)

    def _should_skip_frame(self):
        """Determine if current frame should be skipped based on adaptive logic."""
        if not self.adaptive_skip_enabled:
            # Use fixed frame skipping from original implementation
            return self.frame_count % 5 != 0
        
        # If we don't have enough data yet, use base settings
        if len(self.processing_times) < 5:
            return self.frame_skip_counter % 5 != 0  # Original fixed skipping
        
        # Calculate current average processing time
        avg_processing_time = sum(self.processing_times) / len(self.processing_times)
        current_fps = 1.0 / avg_processing_time if avg_processing_time > 0 else self.target_fps
        
        # If we're meeting target FPS, process the frame
        if current_fps >= self.target_fps:
            self.current_skip_interval = max(1, self.current_skip_interval - 1)
            return False
        
        # If we're significantly below minimum FPS, skip more frames
        if current_fps < self.min_fps:
            # Increase skip interval but cap it
            max_skip = max(1, int(5 * (1 + self.max_skip_ratio)))  # Base skip of 5 with ratio
            self.current_skip_interval = min(max_skip, self.current_skip_interval + 1)
        elif current_fps > self.min_fps * 1.5:
            # We're doing better than minimum, can afford to process more
            self.current_skip_interval = max(1, self.current_skip_interval - 1)
        
        # Skip frame based on current interval
        should_skip = self.frame_skip_counter % max(1, self.current_skip_interval) != 0
        return should_skip

    def stop(self):
        """Stop the frame processor thread."""
        self.stopped.set()

    def _process_recognition_frame(self, frame):
        """Main recognition pipeline: detect → extract → recognize → log"""
        try:
            # 1. DETECT faces
            faces = self.detector.detect(frame)
            
            # Handle case where faces might be a list of lists instead of numpy arrays
            if faces is not None and len(faces) > 0:
                # Convert to numpy arrays if they're lists
                if isinstance(faces[0], list):
                    import numpy as np
                    faces = [np.array(face) for face in faces]
                
                # Extract bounding boxes (ensure they're integers)
                rects = []
                for face in faces:
                    if hasattr(face, 'astype'):
                        # It's a numpy array
                        rect = face[0:4].astype(int)
                    else:
                        # It's a list or other sequence
                        rect = [int(x) for x in face[0:4]]
                    rects.append(rect)
            else:
                rects = []
            
            # 2. EXTRACT embeddings for each face
            embeddings = []
            valid_rects = []
            for rect in rects:
                try:
                    # Ensure rectangle coordinates are within frame bounds
                    x, y, w, h = rect
                    if x >= 0 and y >= 0 and (x + w) <= frame.shape[1] and (y + h) <= frame.shape[0] and w > 0 and h > 0:
                        embedding = self.recognizer.extract_embedding(frame, rect)
                        if embedding is not None:
                            embeddings.append(embedding)
                            valid_rects.append(rect)
                except Exception as e:
                    system_logger.debug(f"[{self.cam_id}] Error extracting embedding for face {rect}: {e}")
            
            # 3. RECOGNIZE each face against FAISS index
            results = []
            for i, embedding in enumerate(embeddings):
                try:
                    employee_id, confidence = self.engine.recognize_face(embedding)
                    rect = valid_rects[i]
                    results.append({
                        'bbox': rect,
                        'employee_id': employee_id,
                        'confidence': float(confidence),
                        'timestamp': time.time()
                    })
                except Exception as e:
                    system_logger.error(f"[{self.cam_id}] Error recognizing face: {e}", exc_info=True)
            
            # 4. UPDATE payload and notify WebSocket clients
            # Encode frame for streaming
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            
            with self.results_lock:
                self.latest_payload = {
                    'type': 'recognition_results',
                    'camera_id': self.cam_id,
                    'frame': frame_b64,
                    'results': results,
                    'timestamp': time.time()
                }
            
            # 5. LOG recognized faces (respect cooldown)
            self._log_recognized_faces(results)
            
        except Exception as e:
            system_logger.error(f"[{self.cam_id}] Error in recognition pipeline: {e}", exc_info=True)

    def _log_recognized_faces(self, results):
        """Log recognized faces with cooldown to prevent spam."""
        current_time = datetime.now()
        for result in results:
            employee_id = result['employee_id']
            confidence = result['confidence']
            object_id = result['bbox']  # Use bbox as a unique identifier for this detection
            
            # Skip logging if recognition failed (employee_id is None)
            if employee_id is None:
                continue
                
            log_key = f"{employee_id}_{object_id}_{self.cam_id}"
            if log_key in self.recently_logged and (current_time - self.recently_logged[log_key]).total_seconds() < self.log_cooldown:
                continue
            recognition_logger.info(
                f"[{self.cam_id}] RECOGNIZED - ID: {employee_id}, "
                f"Confidence: {confidence:.4f}, TrackerID: {object_id}"
            )
            self.engine.db.log_recognition_event(employee_id=employee_id, confidence=float(confidence))
            self.recently_logged[log_key] = current_time
            # cleanup old keys
            self.recently_logged = {
                k: v for k, v in self.recently_logged.items()
                if (current_time - v).total_seconds() < self.log_cooldown * 2
            }

    def _process_registration_frame(self, frame):
        frame_to_process = frame.copy()
        faces = self.detector.detect(frame_to_process)
        payload = {
            "type": "registration_feedback",
            "frame": "",
            "is_good": False,
            "count": len(self.registration_data.get('captured_embeddings', [])),
            "bbox": None,
            "metrics": {},
            "camera_id": self.cam_id
        }
        if len(faces) > 0:
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            is_good, reasons, metrics = self.quality_checker.check_quality(frame_to_process, largest_face)
            payload.update({"bbox": largest_face[0:4], "metrics": metrics})
            if is_good and (time.time() - self.registration_data.get('last_capture_time', 0)) > 1.0:
                payload["is_good"] = True
                embedding = self.recognizer.process_face(frame_to_process, largest_face)
                self.registration_data['captured_embeddings'].append(embedding)
                self.registration_data['last_capture_time'] = time.time()
                payload["count"] = len(self.registration_data['captured_embeddings'])
                if payload["count"] >= self.num_to_capture:
                    self.mode = "AWAITING_METADATA"

        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        payload["frame"] = base64.b64encode(buffer).decode('utf-8')
        with self.results_lock:
            self.latest_payload = payload

    def start_registration(self):
        self.mode = "REGISTRATION"
        self.registration_data = {'captured_embeddings': [], 'last_capture_time': 0}
        return {"status": "success", "message": f"[{self.cam_id}] Registration mode started."}

    def cancel_registration(self):
        self.mode = "RECOGNITION"
        self.registration_data = {}
        return {"status": "success", "message": f"[{self.cam_id}] Registration cancelled."}

    def submit_registration(self, payload: RegistrationPayload):
        if self.mode != "AWAITING_METADATA" or not self.registration_data.get('captured_embeddings'):
            registration_logger.error(f"[{self.cam_id}] Submit called in invalid state.")
            return {"status": "error", "message": "Not in a valid state to submit."}
        template_embedding = normalize(np.mean(self.registration_data['captured_embeddings'], axis=0).reshape(1, -1)).flatten()
        new_user_payload = NewUserPayload(metadata=payload, embedding=template_embedding.tolist())
        success, message = self.engine.register_new_user(new_user_payload)
        self.cancel_registration()
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "error", "message": message}

    def _prepare_recognition_payload(self, frame):
        results_list = []
        for object_id, data in self.tracked_faces.items():
            if data.get("box") is not None:
                info = data.get("info")
                if info:
                    results_list.append({
                        "bbox": data["box"].tolist(),
                        "employee_id": info["name"],
                        "confidence": data.get("similarity", 0.0),
                        "employee_details": {
                            "id": info["employee_id"],
                            "name": info["name"],
                            "department": info["department"],
                            "role": info["role"]
                        }
                    })
                else:
                    results_list.append({
                        "bbox": data["box"].tolist(),
                        "employee_id": "unknown",
                        "confidence": data.get("similarity", 0.0),
                        "employee_details": {
                            "id": "unknown",
                            "name": "Unknown",
                            "department": "N/A",
                            "role": "N/A"
                        }
                    })

        # _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        # frame_b64 = base64.b64encode(buffer).decode('utf-8')
        # with self.results_lock:
        #     self.latest_payload = {
        #         "type": "recognition_results",
        #         "frame": frame_b64,
        #         "results": results_list,
        #         "camera_id": self.cam_id
        #     }

        # tiny_frame = cv2.resize(frame, (320, 180))  # 16x smaller than 1080p
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 10])
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        with self.results_lock:
            self.latest_payload = {
                "type": "recognition_results", 
                "frame": frame_b64, 
                "results": results_list, 
                "camera_id": self.cam_id
            }

    # def _prepare_recognition_payload(self, frame):
    #     results_list = []
    #     for object_id, data in self.tracked_faces.items():
    #         if data.get("box") is not None:
    #             info = data.get("info")
    #             if info:
    #                 results_list.append({
    #                     "bbox": data["box"].tolist(),
    #                     "employee_id": info["name"],
    #                     "confidence": data.get("similarity", 0.0),
    #                     "employee_details": {
    #                         "id": info["employee_id"],
    #                         "name": info["name"],
    #                         "department": info["department"],
    #                         "role": info["role"]
    #                     }
    #                 })
    #             else:
    #                 results_list.append({
    #                     "bbox": data["box"].tolist(),
    #                     "employee_id": "unknown",
    #                     "confidence": data.get("similarity", 0.0),
    #                     "employee_details": {
    #                         "id": "unknown",
    #                         "name": "Unknown",
    #                         "department": "N/A",
    #                         "role": "N/A"
    #                     }
    #                 })

    #     # 20/11/25 SMART FIX: Only send frame data when specifically needed
    #     frame_b64 = None
    #     send_frame = False  # Default to no frame
        
    #     # Condition 1: Send frame only if there are detections AND it's been >2 seconds since last frame
    #     current_time = time.time()
    #     if (len(results_list) > 0 and 
    #         hasattr(self, '_last_frame_sent_time') and 
    #         (current_time - self._last_frame_sent_time) > 2.0):
    #         send_frame = True
    #         self._last_frame_sent_time = current_time
        
    #     # Condition 2: Always send frame in registration mode
    #     if self.mode == "REGISTRATION":
    #         send_frame = True
        
    #     if send_frame:
    #         # 20/11/25 OPTIMIZED: Low resolution for streaming, but keep original for recognition
    #         stream_frame = cv2.resize(frame, (640, 360))  # 4x smaller than 1080p
    #         _, buffer = cv2.imencode('.jpg', stream_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
    #         frame_b64 = base64.b64encode(buffer).decode('utf-8')
    #     else:
    #         frame_b64 = ""  # Empty frame to save bandwidth

    #     with self.results_lock:
    #         self.latest_payload = {
    #             "type": "recognition_results", 
    #             "frame": frame_b64, 
    #             "results": results_list, 
    #             "camera_id": self.cam_id,
    #             "timestamp": current_time  # Add timestamp for client-side management
    #         }

    def _associate_faces_with_trackers(self, faces, tracked_objects):
        current_frame_faces = {}
        for face_data in faces:
            box = face_data[0:4].astype(int)
            cX, cY = int(box[0] + box[2]/2.0), int(box[1] + box[3]/2.0)
            min_dist, matched_id = float('inf'), None
            for (object_id, centroid) in tracked_objects.items():
                dist = np.linalg.norm(np.array(centroid) - np.array((cX, cY)))
                if dist < min_dist:
                    min_dist, matched_id = dist, object_id
            if matched_id is not None:
                current_frame_faces[matched_id] = face_data
        return current_frame_faces

    def _update_box_positions(self, current_frame_faces):
        for object_id, face_data in current_frame_faces.items():
            if object_id in self.tracked_faces:
                self.tracked_faces[object_id]["box"] = face_data[0:4]

    def _cleanup_lost_trackers(self, tracked_objects):
        self.tracked_faces = {id: data for id, data in self.tracked_faces.items() if id in tracked_objects.keys()}

    def get_latest_payload(self):
        with self.results_lock:
            return self.latest_payload

    def stop(self):
        self.stopped.set()

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     system_logger.info("Server starting up...")
#     with open('config.yaml', 'r') as f:
#         config = yaml.safe_load(f)

#     # Init DB + load users once
#     db = Database(config)
#     initial_embeddings, initial_metadata = db.load_all_users_from_db()

#     # Shared engine for ALL cameras
#     engine = RecognitionEngine(config, db, initial_embeddings, initial_metadata)

#     # Build camera workers
#     grabbers: Dict[str, FrameGrabber] = {}
#     processors: Dict[str, FaceProcessor] = {}

#     cameras = config.get('cameras', [])
#     if not cameras:
#         raise RuntimeError("No cameras defined in config.yaml under 'cameras'.")

#     for cam in cameras:
#         cam_id = cam['id']
#         url = cam['url']
#         system_logger.info(f"Initializing camera {cam_id} -> {url}")
#         grabber = FrameGrabber(url, cam_id)
#         processor = FaceProcessor(cam_id, grabber, config, engine)
#         grabbers[cam_id] = grabber
#         processors[cam_id] = processor

#     app.state.config = config
#     app.state.db = db
#     app.state.engine = engine
#     app.state.grabbers = grabbers
#     app.state.processors = processors

#     # Start threads
#     for cam_id in grabbers:
#         grabbers[cam_id].start()
#         processors[cam_id].start()
#     system_logger.info(f"Started {len(grabbers)} camera pipelines.")

#     yield

#     system_logger.info("Server shutting down...")
#     for cam_id in processors:
#         processors[cam_id].stop()
#     for cam_id in grabbers:
#         grabbers[cam_id].stop()
#     app.state.db.close_pool()
#     system_logger.info("All background threads and DB pool stopped cleanly.")
@asynccontextmanager
async def lifespan(app: FastAPI):
    system_logger.info("Server starting up...")
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Initialize database and embeddings
    db = Database(config)
    initial_embeddings, initial_metadata = db.load_all_users_from_db()

    # Shared FAISS engine
    engine = RecognitionEngine(config, db, initial_embeddings, initial_metadata)

    # Shared state containers
    grabbers: Dict[str, FrameGrabber] = {}
    processors: Dict[str, FaceProcessor] = {}

    app.state.config = config
    app.state.db = db
    app.state.engine = engine
    app.state.grabbers = grabbers
    app.state.processors = processors

    cameras = config.get('cameras', [])
    if not cameras:
        raise RuntimeError("No cameras defined in config.yaml under 'cameras'.")

    # --- Helper for threaded camera startup with retry ---
    # def try_start_camera(cam_id, url):
    #     max_retries = 10
    #     for attempt in range(1, max_retries + 1):
    #         try:
    #             grabber = FrameGrabber(url, cam_id)
    #             processor = FaceProcessor(cam_id, grabber, config, engine)
    #             grabbers[cam_id] = grabber
    #             processors[cam_id] = processor
    #             grabber.start()
    #             processor.start()
    #             system_logger.success(f"[{cam_id}] Camera connected and pipeline started.")
    #             return
    #         except Exception as e:
    #             system_logger.error(f"[{cam_id}] Attempt {attempt}/{max_retries} failed: {e}")
    #             if attempt < max_retries:
    #                 system_logger.info(f"[{cam_id}] Retrying connection in 10 seconds...")
    #                 time.sleep(10)
    #             else:
    #                 system_logger.error(f"[{cam_id}] Failed to initialize after {max_retries} attempts. Skipping this camera.")
    def try_start_camera(cam_id, url):
        """Continuously attempt to start and maintain a camera pipeline."""
        backoff = 10  # seconds between retries
        while True:
            try:
                # Try initializing the stream and pipeline
                grabber = FrameGrabber(url, cam_id)
                # Initialize FrameProcessor with all required attributes
                processor = FrameProcessor(config)
                processor.cam_id = cam_id
                processor.grabber = grabber
                processor.engine = engine
                processor.mode = "RECOGNITION"
                
                # Initialize models based on config
                # Always use YOLOv8-Face + MobileFaceNet since we've removed the old models
                processor.detector = YOLOv8FaceDetector(config)
                processor.recognizer = MobileFaceNetRecognizer(config)
                
                processor.quality_checker = QualityChecker(config)
                
                # Initialize tracker based on config
                if config.get('use_deepsort', False) and DEEPSORT_AVAILABLE:
                    try:
                        cfg = get_config()
                        cfg.merge_from_file("deep_sort_pytorch/configs/deep_sort.yaml")
                        processor.tracker = DeepSort(
                            cfg.DEEPSORT.REID_CKPT,
                            max_dist=cfg.DEEPSORT.MAX_DIST,
                            min_confidence=cfg.DEEPSORT.MIN_CONFIDENCE,
                            nms_max_overlap=cfg.DEEPSORT.NMS_MAX_OVERLAP,
                            max_iou_distance=cfg.DEEPSORT.MAX_IOU_DISTANCE,
                            max_age=cfg.DEEPSORT.MAX_AGE,
                            n_init=cfg.DEEPSORT.N_INIT,
                            nn_budget=cfg.DEEPSORT.NN_BUDGET,
                            use_cuda=False
                        )
                        system_logger.info(f"[{cam_id}] Using DeepSORT tracker")
                    except Exception as e:
                        system_logger.error(f"[{cam_id}] Failed to initialize DeepSORT, falling back to CentroidTracker: {e}")
                        processor.tracker = CentroidTracker(
                            max_disappeared=config['max_disappeared_frames'], 
                            max_distance=config['max_distance']
                        )
                else:
                    processor.tracker = CentroidTracker(
                        max_disappeared=config['max_disappeared_frames'], 
                        max_distance=config['max_distance']
                    )
                
                # Initialize other attributes
                processor.results_lock = threading.Lock()
                processor.latest_payload = None
                processor.registration_data = {}
                processor.tracked_faces = {}
                processor.recently_logged = {}
                # Add missing attributes
                processor.use_deepsort = config.get('use_deepsort', False) and DEEPSORT_AVAILABLE
                grabbers[cam_id] = grabber
                processors[cam_id] = processor

                grabber.start()
                processor.start()
                system_logger.success(f"[{cam_id}] Camera connected and pipeline started.")

                # Wait until grabber stops (i.e., camera disconnected or shutdown)
                while not grabber.stopped.is_set():
                    time.sleep(2)

                # Cleanup and retry after disconnect
                system_logger.warning(f"[{cam_id}] Camera disconnected. Will retry in {backoff}s...")
                grabbers.pop(cam_id, None)
                processors.pop(cam_id, None)
                time.sleep(backoff)

            except Exception as e:
                system_logger.error(f"[{cam_id}] Camera init failed: {e}")
                system_logger.info(f"[{cam_id}] Retrying connection in {backoff}s...")
                time.sleep(backoff)


    # --- Start all camera connection threads ---
    # for cam in cameras:
    #     cam_id = cam['id']
    #     url = cam['url']
    #     system_logger.info(f"Initializing camera {cam_id} -> {url}")
    #     threading.Thread(
    #         target=try_start_camera,
    #         args=(cam_id, url),
    #         daemon=True
    #     ).start()

    # system_logger.info(f"Camera initialization threads launched for {len(cameras)} cameras.")
    # --- Start each camera in its own independent retrying thread ---
    for cam in cameras:
        cam_id = cam['id']
        url = cam['url']
        system_logger.info(f"Launching persistent camera thread for {cam_id} -> {url}")
        threading.Thread(
            target=try_start_camera,
            args=(cam_id, url),
            daemon=True
        ).start()

    system_logger.info(f"Launched persistent camera threads for {len(cameras)} cameras.")


    # --- Server startup complete ---
    yield

    # --- Graceful shutdown ---
    system_logger.info("Server shutting down...")
    for cam_id, proc in processors.items():
        proc.stop()
    for cam_id, grabber in grabbers.items():
        grabber.stop()
    app.state.db.close_pool()
    system_logger.info("All background threads and DB pool stopped cleanly.")


app = FastAPI(lifespan=lifespan)

# Add CORS middleware to allow WebSocket connections from frontend
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# --- Attendance page (unchanged) ---
@app.get("/attendance", response_class=HTMLResponse)
async def get_attendance_page():
    try:
        with open("html/attendance.html") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="attendance.html not found")
    
@app.get("/api/cameras")
async def get_cameras():
    cams = app.state.config.get('cameras', [])
    return JSONResponse(
        [{"id": c["id"], "location": c.get("location", "Unknown")} for c in cams]
    )


# --- Global registration via direct embeddings (any client) ---
@app.post("/register", response_class=JSONResponse)
async def register_new_user_endpoint(payload: NewUserPayload):
    success, message = app.state.engine.register_new_user(payload)
    if success:
        return {"status": "success", "message": message}
    else:
        raise HTTPException(status_code=500, detail=message)

# --- Registration flow PER CAMERA ---
@app.post("/start-registration/{camera_id}", response_class=JSONResponse)
async def start_registration(camera_id: str = Path(...)):
    proc = app.state.processors.get(camera_id)
    if not proc:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    return proc.start_registration()

@app.post("/cancel-registration/{camera_id}", response_class=JSONResponse)
async def cancel_registration(camera_id: str = Path(...)):
    proc = app.state.processors.get(camera_id)
    if not proc:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    return proc.cancel_registration()

@app.post("/submit-registration/{camera_id}", response_class=JSONResponse)
async def submit_registration(payload: RegistrationPayload, camera_id: str = Path(...)):
    proc = app.state.processors.get(camera_id)
    if not proc:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    return proc.submit_registration(payload)

# --- WebSocket PER CAMERA ---
@app.websocket("/ws/{camera_id}")
async def websocket_endpoint(websocket: WebSocket, camera_id: str):
    # Allow all WebSocket connections (remove processor check for now)
    await websocket.accept()
    system_logger.info(f"[{camera_id}] New client connected: {websocket.client}")
    
    # Wait for processor to become available (with timeout)
    proc = None
    timeout = 30  # seconds
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        proc = app.state.processors.get(camera_id)
        if proc:
            break
        await asyncio.sleep(0.5)  # Check every 500ms
    
    if not proc:
        system_logger.warning(f"[{camera_id}] No processor available for camera after {timeout} seconds")
        # Send error message to client
        await websocket.send_text(json.dumps({
            "type": "error", 
            "camera_id": camera_id, 
            "message": "Camera processor not available"
        }))
        return
    
    try:
        while True:
            # Get payload from processor
            payload = proc.get_latest_payload()
            if payload is not None:
                await websocket.send_text(json.dumps(payload, cls=NumpyEncoder))
            # await asyncio.sleep(0.04)

            # 20/11/25 IMMEDIATE FIX: Reduce from 25FPS to ~6FPS
            # 20/11/25 ADDITIONAL FIX: Further reduce FPS to prevent overload
            await asyncio.sleep(0.2)  # Changed from 0.15 to 0.2 (5 FPS)

    except WebSocketDisconnect:
        system_logger.warning(f"[{camera_id}] Client disconnected gracefully: {websocket.client}")
    except Exception as e:
        system_logger.error(f"[{camera_id}] Unexpected WebSocket error for client {websocket.client}: {e}", exc_info=True)

# Static files (index.html can list cameras and connect to multiple /ws/{id})
app.mount("/", StaticFiles(directory="html", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    system_logger.info(f"Starting Uvicorn at {config['server_host']}:{config['server_port']}")
    uvicorn.run("server:app", host=config['server_host'], port=config['server_port'], reload=False)