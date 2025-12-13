# mobilefacenet_recognizer.py
# Face recognition using MobileFaceNet model

import cv2
import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import normalize
from logger_config import recognition_logger as logger

class MobileFaceNet(nn.Module):
    """MobileFaceNet implementation for face recognition."""
    
    def __init__(self, embedding_size=128):
        super(MobileFaceNet, self).__init__()
        self.embedding_size = embedding_size
        
        # Define a simplified MobileFaceNet architecture
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1, groups=64),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, kernel_size=1, stride=1, padding=0),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, kernel_size=3, stride=2, padding=1, groups=128),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 256, kernel_size=1, stride=1, padding=0),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1))
        )
        
        self.classifier = nn.Linear(256, self.embedding_size)
        
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        x = torch.nn.functional.normalize(x, p=2, dim=1)
        return x

class MobileFaceNetRecognizer:
    """Handles face recognition using MobileFaceNet model."""
    
    def __init__(self, config):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        try:
            # Initialize MobileFaceNet model
            self.model = MobileFaceNet()
            self.model.to(self.device)
            self.model.eval()
            
            # Reference landmarks for face alignment
            self.reference_landmarks = np.array([
                [38.2946, 51.6963], [73.5318, 51.5014],
                [56.0252, 71.7366], [41.5493, 92.3655],
                [70.7299, 92.2041]
            ], dtype=np.float32)
            
            logger.info("MobileFaceNet Recognizer initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MobileFaceNet Recognizer: {e}", exc_info=True)
            raise e
    
    def _align_face(self, frame, landmarks):
        """Aligns a face using a similarity transform based on 5 landmarks."""
        transform_matrix, _ = cv2.estimateAffinePartial2D(landmarks, self.reference_landmarks)
        aligned_face = cv2.warpAffine(frame, transform_matrix, (112, 112), borderValue=0.0)
        return aligned_face
    
    def _get_embedding(self, aligned_face):
        """Extracts a 128-dimensional feature embedding from an aligned face."""
        # Convert to tensor
        face_tensor = torch.from_numpy(aligned_face).permute(2, 0, 1).unsqueeze(0).float()
        face_tensor = face_tensor.to(self.device)
        
        # Normalize
        face_tensor = (face_tensor - 127.5) / 127.5
        
        # Get embedding
        with torch.no_grad():
            embedding = self.model(face_tensor)
            embedding = embedding.cpu().numpy().flatten()
        
        # Log embedding dimension for debugging
        logger.debug(f"MobileFaceNet embedding dimension: {embedding.shape}")
        
        # Pad embedding from 128 to 512 dimensions to match existing database
        if embedding.shape[0] == 128:
            padded_embedding = np.pad(embedding, (0, 384), mode='constant', constant_values=0)
            logger.debug(f"Padded embedding dimension: {padded_embedding.shape}")
            return padded_embedding
        
        return embedding
    
    def extract_embedding(self, frame, rect):
        """Extracts embedding from a face rectangle."""
        logger.debug("Extracting embedding using MobileFaceNet.")
        
        # Create face_data format expected by process_face
        # [x, y, width, height]
        x, y, w, h = rect
        face_data = np.array([x, y, w, h], dtype=np.float32)
        
        # Call process_face with the rect data
        return self.process_face(frame, face_data)
    
    def process_face(self, frame, face_data):
        """Processes a single detected face to get its embedding."""
        logger.debug("Processing face to generate embedding using MobileFaceNet.")
        
        # Extract landmarks from face_data
        # face_data format: [x, y, width, height, landmark1_x, landmark1_y, ..., landmark5_x, landmark5_y]
        if len(face_data) >= 14:  # Check if landmarks are available
            landmarks = face_data[4:14].reshape(5, 2).astype(np.float32)
        else:
            # Use placeholder landmarks if not available
            h, w = frame.shape[:2]
            landmarks = np.array([
                [w * 0.3, h * 0.3],  # Left eye
                [w * 0.7, h * 0.3],  # Right eye
                [w * 0.5, h * 0.5],  # Nose
                [w * 0.3, h * 0.7],  # Left mouth corner
                [w * 0.7, h * 0.7]   # Right mouth corner
            ], dtype=np.float32)
        
        aligned_face = self._align_face(frame, landmarks)
        embedding = self._get_embedding(aligned_face)
        
        logger.debug("Successfully generated embedding using MobileFaceNet.")
        return embedding