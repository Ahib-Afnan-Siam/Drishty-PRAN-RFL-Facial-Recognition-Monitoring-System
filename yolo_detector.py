# yolo_detector.py
# Face detection using YOLOv8 model

import cv2
import numpy as np
import torch
import os
from logger_config import detection_logger as logger

class YOLOv8FaceDetector:
    """Handles face detection using YOLOv8 model."""
    
    def __init__(self, config):
        try:
            import torch
            import cv2
            import logging
            
            # Add safe globals for PyTorch 2.6+ compatibility
            if hasattr(torch.serialization, 'add_safe_globals'):
                from ultralytics.nn.tasks import DetectionModel
                from torch.nn import Sequential, Conv2d, BatchNorm2d
                from ultralytics.nn.modules import Conv
                from torch.nn.modules.activation import SiLU
                torch.serialization.add_safe_globals([DetectionModel, Sequential, Conv, Conv2d, BatchNorm2d, SiLU])
            
            # Remove the self.logger line to use the imported logger directly
            # self.logger = logging.getLogger(__name__)
            
            # Load YOLOv8 model with weights_only=False for PyTorch 2.6+ compatibility
            model_path = config.get('yolo_model_path', 'models/yolov8n-face.pt')
            
            # Handle PyTorch 2.6+ compatibility issue by explicitly setting weights_only=False
            # This is safe since we're loading a trusted model
            import functools
            original_load = torch.load
            torch.load = functools.partial(original_load, weights_only=False)
            
            # Try to load using ultralytics first
            try:
                from ultralytics import YOLO
                self.model = YOLO(model_path)
            except Exception as e:
                logger.warning(f"Failed to load model with ultralytics: {e}")
                # Fallback to direct torch load
                self.model = torch.load(model_path, map_location='cpu')
            
            # Restore original torch.load
            torch.load = original_load
            
            # Set fixed input dimensions for reduced resolution (640x360)
            self.input_height = 360
            self.input_width = 640
            
            self.confidence_threshold = config['yolo_confidence_threshold']
            self.nms_threshold = config['yolo_nms_threshold']
            
            logger.info(f"YOLOv8 Face Detector initialized successfully with model: {model_path}")
        except Exception as e:
            logger.error(f"Failed to initialize YOLOv8 Face Detector: {e}", exc_info=True)
            raise
    
    def detect(self, frame):
        """Detects faces in a given frame using YOLOv8 model."""
        try:
            # Resize frame to reduced resolution
            resized_frame = cv2.resize(frame, (self.input_width, self.input_height))
            
            # Check if model is a ultralytics YOLO model
            if hasattr(self.model, 'predict'):
                # For ultralytics, we need to save the frame to a temporary file
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                    temp_path = tmp_file.name
                    cv2.imwrite(temp_path, resized_frame)
                
                try:
                    # Run inference with reduced resolution
                    results = self.model(temp_path, verbose=False)
                    detections = []
                    
                    # Process results
                    for result in results:
                        boxes = result.boxes
                        if boxes is not None:
                            for box in boxes:
                                if box.conf[0] > self.confidence_threshold:
                                    # Get box coordinates
                                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                    
                                    # Scale coordinates back to original frame size
                                    scale_x = frame.shape[1] / self.input_width
                                    scale_y = frame.shape[0] / self.input_height
                                    x1 *= scale_x
                                    y1 *= scale_y
                                    x2 *= scale_x
                                    y2 *= scale_y
                                    
                                    width = x2 - x1
                                    height = y2 - y1
                                    confidence = box.conf[0].cpu().item()
                                    
                                    detections.append([x1, y1, width, height, confidence])
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            else:
                # For direct model inference, we need to preprocess the frame
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                
                # Normalize and create batch dimension
                import numpy as np
                input_tensor = np.expand_dims(rgb_frame, axis=0).astype(np.float32)
                input_tensor = input_tensor / 255.0  # Normalize to [0, 1]
                input_tensor = np.transpose(input_tensor, (0, 3, 1, 2))  # Change to NCHW format
                
                # Convert to torch tensor
                import torch
                input_tensor = torch.from_numpy(input_tensor)
                
                # Run inference
                with torch.no_grad():
                    results = self.model(input_tensor)
                
                # Return empty detections for now as this would require model-specific post-processing
                detections = []
            
            num_faces = len(detections)
            logger.debug(f"Detected {num_faces} faces using YOLOv8 model.")
            return detections
            
        except Exception as e:
            logger.error(f"Error during face detection: {e}", exc_info=True)
            return []