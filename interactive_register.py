
# interactive_register.py

import cv2
import yaml
import numpy as np
import time
import requests # NEW
import json # NEW
from sklearn.preprocessing import normalize

from logger_config import registration_logger as logger
from detector import FaceDetector
from recognizer import FaceRecognizer
from quality_checker import QualityChecker

# (UI Constants and draw_status_panel function remain unchanged)
CAPTURE_WINDOW_NAME = "Interactive Registration"; NUM_IMAGES_TO_CAPTURE = 10; CAPTURE_COOLDOWN_SEC = 1.0
COLOR_GREEN = (0, 255, 0); COLOR_RED = (0, 0, 255); COLOR_BLUE = (255, 100, 0); COLOR_WHITE = (255, 255, 255)
def draw_status_panel(frame, metrics, config):
    y_offset = 30; panel_x = 20
    def draw_metric(label, value, target, condition):
        nonlocal y_offset
        color = COLOR_GREEN if condition else COLOR_RED
        text = f"{label}: {value} (Req: {target})"
        cv2.putText(frame, text, (panel_x, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        y_offset += 20
    clarity = metrics['clarity']; target_clarity = config['min_blur_clarity']
    draw_metric("Clarity", f"{clarity:.0f}", f"> {target_clarity}", clarity > target_clarity)
    brightness = metrics['brightness']; min_bright, max_bright = config['min_brightness'], config['max_brightness']
    draw_metric("Brightness", f"{brightness:.0f}", f"{min_bright}-{max_bright}", min_bright < brightness < max_bright)
    yaw, pitch, roll = abs(metrics['yaw']), abs(metrics['pitch']), abs(metrics['roll'])
    max_yaw, max_pitch, max_roll = config['max_pose_yaw'], config['max_pose_pitch'], config['max_pose_roll']
    draw_metric("Pose (Y,P,R)", f"{yaw:.0f}, {pitch:.0f}, {roll:.0f}", f"< {max_yaw}", yaw < max_yaw and pitch < max_pitch and roll < max_roll)
    (w, h) = metrics['size']; target_size = config['min_face_size']
    draw_metric("Face Size", f"{w}x{h}", f"> {target_size}", w > target_size and h > target_size)

def main():
    with open('config.yaml', 'r') as f: config = yaml.safe_load(f)
    logger.info("Starting Interactive Registration UI (Client Mode).")

    detector = FaceDetector(config)
    recognizer = FaceRecognizer(config)
    quality_checker = QualityChecker(config)
    
    cap = cv2.VideoCapture(config['camera_url'], cv2.CAP_FFMPEG)
    # ... (Image capture loop remains unchanged) ...
    if not cap.isOpened(): logger.error(f"Error: Could not open camera stream at {config['camera_url']}"); return
    captured_images, last_capture_time = [], 0
    while len(captured_images) < NUM_IMAGES_TO_CAPTURE:
        ret, frame = cap.read()
        if not ret: break
        display_frame = frame.copy()
        faces = detector.detect(frame)
        progress_text = f"Progress: {len(captured_images)}/{NUM_IMAGES_TO_CAPTURE}"
        if len(faces) > 0:
            largest_face = max(faces, key=lambda face: face[2] * face[3])
            box = largest_face[0:4].astype(int)
            is_good, reasons, metrics = quality_checker.check_quality(frame, largest_face)
            draw_status_panel(display_frame, metrics, config)
            if is_good:
                feedback_msg = "Hold Still..."
                box_color = COLOR_GREEN
                if time.time() - last_capture_time > CAPTURE_COOLDOWN_SEC:
                    captured_images.append(frame)
                    last_capture_time = time.time()
                    logger.info(f"Captured high-quality image #{len(captured_images)}.")
                    (x, y, w, h) = box
                    display_frame[y:y+h, x:x+w] = cv2.addWeighted(display_frame[y:y+h, x:x+w], 0.3, np.full((h, w, 3), 255, np.uint8), 0.7, 0)
            else: feedback_msg = f"Guidance: {reasons[0]}"; box_color = COLOR_RED
            cv2.rectangle(display_frame, tuple(box[:2]), tuple(box[:2] + box[2:]), box_color, 2)
            cv2.putText(display_frame, feedback_msg, (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2)
        cv2.putText(display_frame, progress_text, (20, display_frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, COLOR_WHITE, 2)
        cv2.imshow(CAPTURE_WINDOW_NAME, display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): logger.warning("Registration quit by user."); break
    cap.release(); cv2.destroyAllWindows()
    if len(captured_images) < NUM_IMAGES_TO_CAPTURE: logger.error("Registration incomplete. Exiting."); return
    logger.success("Image capture complete.")

    # ... (Embedding generation logic remains unchanged) ...
    person_embeddings = []
    logger.info("Processing captured images to generate embeddings...")
    for img in captured_images:
        faces = detector.detect(img)
        if len(faces) > 0:
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            embedding = recognizer.process_face(img, largest_face)
            person_embeddings.append(embedding.flatten())
    if not person_embeddings:
        logger.error("Failed to generate any embeddings. Registration aborted."); print("\nâŒ Registration Failed.")
        return
    logger.success(f"Successfully generated {len(person_embeddings)} embeddings.")

    # ... (Metadata collection remains unchanged) ...
    print("\n--- Image Processing Successful ---\nPlease provide the following details:")
    while True:
        employee_id_str = input("Enter Employee ID (numbers only): ").strip()
        if employee_id_str.isdigit(): employee_id = int(employee_id_str); break
        print("Invalid ID. Please enter numbers only.")
    name, department, role = input("Enter Name: ").strip(), input("Enter Department: ").strip(), input("Enter Role: ").strip()
    
    # --- NEW: Send data to the server via API ---
    template_embedding = normalize(np.mean(person_embeddings, axis=0).reshape(1, -1)).flatten()
    
    payload = {
        "metadata": {'employee_id': employee_id, 'name': name, 'department': department, 'role': role},
        "embedding": template_embedding.tolist()
    }
    
    server_url = f"http://{config['server_host']}:{config['server_port']}/register"
    logger.info(f"Sending registration data for {name} to server at {server_url}...")
    
    try:
        response = requests.post(server_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
        response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)
        
        response_data = response.json()
        if response_data.get("status") == "success":
            logger.success(f"Server successfully registered {name} (ID: {employee_id})!")
            print(f"\nâœ… Registration for {name} was successful!")
        else:
            logger.error(f"Server returned an error: {response_data.get('message', 'Unknown error')}")
            print(f"\nâŒ Registration failed: {response_data.get('message', 'Unknown error')}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to the server: {e}", exc_info=True)
        print(f"\nâŒ Registration failed: Could not connect to the recognition server at {server_url}.")

if __name__ == "__main__":
    main()