# # tracker.py

# from collections import OrderedDict
# from scipy.spatial import distance as dist
# import numpy as np

# class CentroidTracker:
#     """
#     A simple object tracker based on centroid distances.
#     Maintains a stable ID for detected objects across frames.
#     """
#     def __init__(self, max_disappeared=50):
#         self.next_object_id = 0
#         self.objects = OrderedDict()
#         self.disappeared = OrderedDict()
#         self.max_disappeared = max_disappeared

#     def register(self, centroid):
#         """Registers a new object with a new ID."""
#         self.objects[self.next_object_id] = centroid
#         self.disappeared[self.next_object_id] = 0
#         self.next_object_id += 1

#     def deregister(self, object_id):
#         """Deregisters an object that has been lost for too long."""
#         del self.objects[object_id]
#         del self.disappeared[object_id]

#     def update(self, rects):
#         """
#         Updates the state of tracked objects based on new bounding boxes.
        
#         Args:
#             rects (list): A list of (startX, startY, endX, endY) bounding boxes.
        
#         Returns:
#             OrderedDict: A dictionary mapping object IDs to their centroids.
#         """
#         if len(rects) == 0:
#             for object_id in list(self.disappeared.keys()):
#                 self.disappeared[object_id] += 1
#                 if self.disappeared[object_id] > self.max_disappeared:
#                     self.deregister(object_id)
#             return self.objects

#         input_centroids = np.zeros((len(rects), 2), dtype="int")
#         for (i, (startX, startY, endX, endY)) in enumerate(rects):
#             cX = int((startX + endX) / 2.0)
#             cY = int((startY + endY) / 2.0)
#             input_centroids[i] = (cX, cY)

#         if len(self.objects) == 0:
#             for i in range(len(input_centroids)):
#                 self.register(input_centroids[i])
#         else:
#             object_ids = list(self.objects.keys())
#             object_centroids = list(self.objects.values())
            
#             D = dist.cdist(np.array(object_centroids), input_centroids)
#             rows = D.min(axis=1).argsort()
#             cols = D.argmin(axis=1)[rows]
            
#             used_rows = set()
#             used_cols = set()
            
#             for (row, col) in zip(rows, cols):
#                 if row in used_rows or col in used_cols:
#                     continue
                
#                 object_id = object_ids[row]
#                 self.objects[object_id] = input_centroids[col]
#                 self.disappeared[object_id] = 0
#                 used_rows.add(row)
#                 used_cols.add(col)

#             unused_rows = set(range(0, D.shape[0])).difference(used_rows)
#             unused_cols = set(range(0, D.shape[1])).difference(used_cols)

#             if D.shape[0] >= D.shape[1]:
#                 for row in unused_rows:
#                     object_id = object_ids[row]
#                     self.disappeared[object_id] += 1
#                     if self.disappeared[object_id] > self.max_disappeared:
#                         self.deregister(object_id)
#             else:
#                 for col in unused_cols:
#                     self.register(input_centroids[col])
        
#         return self.objects





from collections import OrderedDict
from scipy.spatial import distance as dist
import numpy as np

def cosine_similarity(a, b):
    """Compute cosine similarity between two 1D arrays."""
    a = a.flatten()
    b = b.flatten()
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

class CentroidTracker:
    """
    Embedding-aware centroid tracker.
    Combines spatial tracking with face embedding verification to prevent ID drift.
    """
    def __init__(self, max_disappeared=50, max_distance=50, recognition_threshold=0.5):
        self.next_object_id = 0
        self.objects = OrderedDict()       # object_id -> centroid
        self.disappeared = OrderedDict()   # object_id -> disappeared frames
        self.embeddings = OrderedDict()    # object_id -> last known embedding
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.recognition_threshold = recognition_threshold

    def register(self, centroid, embedding=None):
        """Register a new object with a centroid and optional embedding."""
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.embeddings[self.next_object_id] = embedding
        self.next_object_id += 1

    def deregister(self, object_id):
        """Remove an object."""
        del self.objects[object_id]
        del self.disappeared[object_id]
        del self.embeddings[object_id]

    def update(self, rects, embeddings=None):
        """
        Update tracked objects.

        Args:
            rects (list): list of bounding boxes (startX, startY, endX, endY)
            embeddings (list): list of embeddings corresponding to rects
        Returns:
            OrderedDict: object_id -> centroid
        """
        if embeddings is None:
            embeddings = [None] * len(rects)

        if len(rects) == 0:
            # No detections: increment disappeared counters
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        # Compute centroids
        input_centroids = np.zeros((len(rects), 2), dtype="int")
        for i, (startX, startY, endX, endY) in enumerate(rects):
            input_centroids[i] = ((startX + endX) // 2, (startY + endY) // 2)

        if len(self.objects) == 0:
            # No existing objects: register all
            for i in range(len(input_centroids)):
                self.register(input_centroids[i], embeddings[i])
        else:
            # Match existing objects to new detections
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            D = dist.cdist(np.array(object_centroids), input_centroids)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows = set()
            used_cols = set()

            for row, col in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue

                object_id = object_ids[row]
                centroid_dist = D[row, col]

                # Check distance threshold
                if centroid_dist > self.max_distance:
                    continue

                # Check embedding similarity if available
                current_embedding = embeddings[col]
                last_embedding = self.embeddings.get(object_id)
                if current_embedding is not None and last_embedding is not None:
                    sim = cosine_similarity(current_embedding, last_embedding)
                    if sim < self.recognition_threshold:
                        # Too different: do not assign this ID
                        continue
                    else:
                        # Update embedding
                        self.embeddings[object_id] = current_embedding

                # Update centroid and reset disappearance counter
                self.objects[object_id] = input_centroids[col]
                self.disappeared[object_id] = 0
                used_rows.add(row)
                used_cols.add(col)

            # Handle unassigned rows (lost objects)
            unused_rows = set(range(D.shape[0])) - used_rows
            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)

            # Handle unassigned cols (new objects)
            unused_cols = set(range(D.shape[1])) - used_cols
            for col in unused_cols:
                self.register(input_centroids[col], embeddings[col])

        return self.objects
