# register_faces.py

import os
import yaml
import numpy as np
import pandas as pd
import requests
import json
from sklearn.preprocessing import normalize

from logger_config import registration_logger as logger
from detector import FaceDetector
from recognizer import FaceRecognizer
from quality_checker import QualityChecker
from utils import load_and_correct_orientation

# def main():
#     with open('config.yaml', 'r') as f: config = yaml.safe_load(f)
#     logger.info("Starting professional face registration batch process (Client Mode).")

#     server_url = f"http://{config['server_host']}:{config['server_port']}/register"

#     try:
#         # Initialize components
#         detector = FaceDetector(config)
#         recognizer = FaceRecognizer(config)
#         quality_checker = QualityChecker(config)

#         try:
#             employee_df = pd.read_csv(config['employee_data_csv'])
#         except FileNotFoundError:
#             logger.error(f"Error: The file {config['employee_data_csv']} was not found.")
#             return

#         successful_registrations = 0
#         for index, row in employee_df.iterrows():
#             name, employee_id = row['name'], row['employee_id']
#             # ... (Image processing loop remains unchanged) ...
#             logger.info(f"Processing images for {name} (ID: {employee_id})")
#             image_dir = row['image_path']
#             if not os.path.isdir(image_dir): logger.warning(f"Directory not found for {name}: {image_dir}"); continue
#             image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
#             if not image_files: logger.warning(f"No images found for {name} in {image_dir}"); continue
#             person_embeddings = []
#             for image_file in image_files:
#                 image_path = os.path.join(image_dir, image_file)
#                 frame = load_and_correct_orientation(image_path)
#                 if frame is None: continue
#                 faces = detector.detect(frame)
#                 if not faces: continue
#                 largest_face = max(faces, key=lambda face: face[2] * face[3])
#                 is_good, _, _ = quality_checker.check_quality(frame, largest_face)
#                 if not is_good: continue
#                 embedding = recognizer.process_face(frame, largest_face)
#                 person_embeddings.append(embedding.flatten())
            
#             if not person_embeddings:
#                 logger.error(f"Failed to generate valid embeddings for {name}. Skipping."); continue

#             # --- NEW: Send data to the server via API ---
#             template_embedding = normalize(np.mean(person_embeddings, axis=0).reshape(1, -1)).flatten()
            
#             payload = {
#                 "metadata": {'employee_id': int(employee_id), 'name': name, 'department': row['department'], 'role': row['role']},
#                 "embedding": template_embedding.tolist()
#             }
            
#             logger.info(f"Sending registration data for {name} to server...")
#             try:
#                 response = requests.post(server_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
#                 response.raise_for_status()
#                 successful_registrations += 1
#                 logger.success(f"Server successfully registered {name} (ID: {employee_id}).")
#             except requests.exceptions.RequestException as e:
#                 logger.error(f"Failed to register {name} via server API: {e}")

#         logger.info(f"Batch registration process finished. Successfully sent {successful_registrations} registration requests.")

#     except Exception as e:
#         logger.error(f"An unexpected error occurred during the batch process: {e}", exc_info=True)

# if __name__ == "__main__":
#     main()

# register_faces.py

# ... existing code ...

def main():
    with open('config.yaml', 'r') as f: config = yaml.safe_load(f)
    logger.info("Starting professional face registration batch process (Client Mode).")

    server_url = f"http://{config['server_host']}:{config['server_port']}/register"

    try:
        # Initialize components
        detector = FaceDetector(config)
        recognizer = FaceRecognizer(config)
        quality_checker = QualityChecker(config)

        try:
            employee_df = pd.read_csv(config['employee_data_csv'])
        except FileNotFoundError:
            logger.error(f"Error: The file {config['employee_data_csv']} was not found.")
            return

        successful_registrations = 0
        for index, row in employee_df.iterrows():
            name, employee_id = row['name'], row['employee_id']
            logger.info(f"Processing images for {name} (ID: {employee_id})")
            image_dir = row['image_path']
            if not os.path.isdir(image_dir): 
                logger.warning(f"Directory not found for {name}: {image_dir}")
                continue
                
            image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if not image_files: 
                logger.warning(f"No images found for {name} in {image_dir}")
                continue
                
            person_embeddings = []
            for image_file in image_files:
                image_path = os.path.join(image_dir, image_file)
                frame = load_and_correct_orientation(image_path)
                if frame is None: 
                    continue
                    
                faces = detector.detect(frame)
                if len(faces) == 0:  # Fixed: explicit length check instead of truthiness
                    continue
                    
                largest_face = max(faces, key=lambda face: face[2] * face[3])
                is_good, _, _ = quality_checker.check_quality(frame, largest_face)
                if not is_good: 
                    continue
                    
                embedding = recognizer.process_face(frame, largest_face)
                person_embeddings.append(embedding.flatten())
            
            # FIX: Check if the list is empty using len() instead of truthiness
            if len(person_embeddings) == 0:
                logger.error(f"Failed to generate valid embeddings for {name}. Skipping.")
                continue

            # --- Send data to the server via API ---
            template_embedding = normalize(np.mean(person_embeddings, axis=0).reshape(1, -1)).flatten()
            
            payload = {
                "metadata": {
                    'employee_id': int(employee_id), 
                    'name': name, 
                    'department': row['department'], 
                    'role': row['role']
                },
                "embedding": template_embedding.tolist()
            }
            
            logger.info(f"Sending registration data for {name} to server...")
            try:
                response = requests.post(server_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
                response.raise_for_status()
                successful_registrations += 1
                logger.success(f"Server successfully registered {name} (ID: {employee_id}).")
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to register {name} via server API: {e}")

        logger.info(f"Batch registration process finished. Successfully sent {successful_registrations} registration requests.")

    except Exception as e:
        logger.error(f"An unexpected error occurred during the batch process: {e}", exc_info=True)

if __name__ == "__main__":
    main()