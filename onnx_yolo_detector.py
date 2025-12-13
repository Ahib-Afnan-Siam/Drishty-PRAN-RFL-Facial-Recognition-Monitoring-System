# onnx_yolo_detector.py
# Face detection using YOLOv8 ONNX model for better CPU performance

import cv2
import numpy as np
import onnxruntime as ort
import os
from logger_config import detection_logger as logger

class ONNXYOLOv8FaceDetector:
    """Handles face detection using YOLOv8 ONNX model."""
    
    def __init__(self, config):
        try:
            import onnxruntime as ort
            import numpy as np
            import cv2
            import logging
            import os
            
            self.logger = logging.getLogger(__name__)
            
            # Load ONNX model - use .onnx file instead of .pt
            model_path = config.get('yolo_model_path', 'models/yolov8n-face.pt')
            # Replace .pt extension with .onnx if needed
            if model_path.endswith('.pt'):
                onnx_model_path = model_path.replace('.pt', '.onnx')
            else:
                onnx_model_path = model_path
                
            # Check if the ONNX model exists
            if not os.path.exists(onnx_model_path):
                # Try default ONNX model path
                if os.path.exists('models/yolov8n-face.onnx'):
                    onnx_model_path = 'models/yolov8n-face.onnx'
                elif os.path.exists('yolov8n.onnx'):
                    onnx_model_path = 'yolov8n.onnx'
                else:
                    raise FileNotFoundError(f"No ONNX model found. Checked: {onnx_model_path}, models/yolov8n-face.onnx, yolov8n.onnx")
            
            self.session = ort.InferenceSession(onnx_model_path)
            self.input_name = self.session.get_inputs()[0].name
            
            # Set fixed input dimensions for reduced resolution (640x360)
            self.input_height = 360
            self.input_width = 640
            
            self.confidence_threshold = config['yolo_confidence_threshold']
            self.nms_threshold = config['yolo_nms_threshold']
            
            self.logger.info(f"ONNX YOLOv8 Face Detector initialized successfully with model: {onnx_model_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize ONNX YOLOv8 Face Detector: {e}", exc_info=True)
            raise
    
    def detect(self, frame):
        """Detects faces in a given frame using YOLOv8 ONNX model."""
        try:
            # Preprocess frame with reduced resolution
            resized_frame = cv2.resize(frame, (self.input_width, self.input_height))
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            
            # Normalize and create batch dimension
            input_tensor = np.expand_dims(rgb_frame, axis=0).astype(np.float32)
            input_tensor = input_tensor / 255.0  # Normalize to [0, 1]
            input_tensor = np.transpose(input_tensor, (0, 3, 1, 2))  # Change to NCHW format
            
            # Run inference
            outputs = self.session.run(None, {self.input_name: input_tensor})
            
            # Post-process results
            detections = self._postprocess(outputs[0][0], frame.shape[1], frame.shape[0], self.input_width, self.input_height)
            
            num_faces = len(detections)
            self.logger.debug(f"Detected {num_faces} faces using ONNX YOLOv8 model.")
            return detections
            
        except Exception as e:
            self.logger.error(f"Error during face detection: {e}", exc_info=True)
            return []
    
    def _postprocess(self, outputs, orig_width, orig_height, input_width, input_height):
        """Post-process the ONNX model outputs to extract face detections."""
        # YOLOv8 outputs shape: (5, 8400) where 5 = [x, y, w, h, conf]
        # For face detection, we expect only one class (face)
        
        detections = []
        
        # Extract boxes, scores
        boxes = outputs[:4, :].T  # Transpose to get (8400, 4)
        scores = outputs[4, :]    # Confidence scores
        
        # Filter by confidence threshold
        valid_indices = scores > self.confidence_threshold
        boxes = boxes[valid_indices]
        scores = scores[valid_indices]
        
        if len(boxes) == 0:
            return detections
        
        # Convert from center format (x, y, w, h) to corner format (x1, y1, x2, y2)
        boxes_xyxy = np.copy(boxes)
        boxes_xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2  # x1 = cx - w/2
        boxes_xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2  # y1 = cy - h/2
        boxes_xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2  # x2 = cx + w/2
        boxes_xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2  # y2 = cy + h/2
        
        # Scale boxes to original frame size
        scale_x = orig_width / input_width
        scale_y = orig_height / input_height
        boxes_xyxy[:, [0, 2]] *= scale_x
        boxes_xyxy[:, [1, 3]] *= scale_y
        
        # Apply NMS
        indices = cv2.dnn.NMSBoxes(
            boxes_xyxy.tolist(),
            scores.tolist(),
            self.confidence_threshold,
            self.nms_threshold
        )
        
        if len(indices) > 0:
            # Flatten indices if needed (NMSBoxes can return nested array)
            if isinstance(indices[0], list) or isinstance(indices[0], np.ndarray):
                indices = [i[0] for i in indices]
            
            for i in indices:
                x1, y1, x2, y2 = boxes_xyxy[i]
                conf = scores[i]
                # Return in format [x1, y1, width, height, confidence]
                detections.append([x1, y1, x2 - x1, y2 - y1, conf])
        
        return detections

# Test the ONNX detector
if __name__ == "__main__":
    import yaml
    import os
    
    # Load configuration
    config = yaml.safe_load(open('config.yaml'))
    
    try:
        detector = ONNXYOLOv8FaceDetector(config)
        print("ONNX YOLOv8 Face Detector initialized successfully!")
    except Exception as e:
        print(f"Failed to initialize ONNX YOLOv8 Face Detector: {e}")