# openvino_yolo_detector.py
# Face detection using YOLOv8 OpenVINO model for maximum Intel CPU performance

import cv2
import numpy as np
import os
from logger_config import detection_logger as logger

class OpenVINOYOLOv8FaceDetector:
    """Handles face detection using YOLOv8 OpenVINO model for maximum Intel CPU performance."""
    
    def __init__(self, config):
        try:
            import openvino as ov
            from openvino.runtime import Core
            import numpy as np
            import cv2
            import logging
            import os
            
            self.logger = logging.getLogger(__name__)
            
            # Check for specialized face model first
            model_paths = [
                ("models/yolov8n-face-openvino.xml", "models/yolov8n-face-openvino.bin"),  # Specialized face model
                ("yolov8n-openvino.xml", "yolov8n-openvino.bin")                         # General model
            ]
            
            model_xml_path = None
            model_bin_path = None
            for xml_path, bin_path in model_paths:
                if os.path.exists(xml_path) and os.path.exists(bin_path):
                    model_xml_path = xml_path
                    model_bin_path = bin_path
                    break
            
            if model_xml_path is None or model_bin_path is None:
                raise FileNotFoundError("No YOLOv8 OpenVINO model found. Please ensure the .xml and .bin files exist.")
            
            # Create OpenVINO Core
            self.core = Core()
            
            # Read the model
            self.model = self.core.read_model(model=model_xml_path, weights=model_bin_path)
            
            # Compile the model for CPU
            self.compiled_model = self.core.compile_model(model=self.model, device_name="CPU")
            
            # Get input layer
            self.input_layer = self.compiled_model.input(0)
            
            # Set fixed input dimensions for reduced resolution (640x360)
            self.input_height = 360
            self.input_width = 640
            
            self.confidence_threshold = config['yolo_confidence_threshold']
            self.nms_threshold = config['yolo_nms_threshold']
            
            self.logger.info(f"OpenVINO YOLOv8 Face Detector initialized successfully with model: {model_xml_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenVINO YOLOv8 Face Detector: {e}", exc_info=True)
            raise
    
    def detect(self, frame):
        """Detects faces in a given frame using YOLOv8 OpenVINO model."""
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
            results = self.compiled_model([input_tensor])
            outputs = results[self.compiled_model.output(0)]
            
            # Post-process results
            detections = self._postprocess(outputs[0], frame.shape[1], frame.shape[0], self.input_width, self.input_height)
            
            num_faces = len(detections)
            self.logger.debug(f"Detected {num_faces} faces using OpenVINO YOLOv8 model.")
            return detections
            
        except Exception as e:
            self.logger.error(f"Error during face detection: {e}", exc_info=True)
            return []
    
    def _postprocess(self, outputs, orig_width, orig_height, input_width, input_height):
        """Post-process the OpenVINO model outputs to extract face detections."""
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

# Test the OpenVINO detector
if __name__ == "__main__":
    import yaml
    import os
    
    # Load configuration
    config = yaml.safe_load(open('config.yaml'))
    
    try:
        detector = OpenVINOYOLOv8FaceDetector(config)
        print("OpenVINO YOLOv8 Face Detector initialized successfully!")
    except Exception as e:
        print(f"Failed to initialize OpenVINO YOLOv8 Face Detector: {e}")