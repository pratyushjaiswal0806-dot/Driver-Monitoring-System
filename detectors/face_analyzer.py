"""MediaPipe Face Mesh wrapper for 468 landmark detection."""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, List
import config

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover
    mp = None


@dataclass
class FaceData:
    """Container for detected face data."""
    landmarks: np.ndarray           # 468 landmarks (x, y, z)
    normalized_landmarks: np.ndarray  # Same data, different shape
    face_bbox: tuple                 # (x, y, w, h)
    detection_confidence: float
    face_present: bool
    fps: float = 0.0

    def get_landmark_xy(self, index: int, frame_shape: tuple) -> tuple:
        """Get landmark as (x, y) in pixel coordinates."""
        if index < 0 or index >= len(self.landmarks):
            return (0, 0)
        x = int(self.landmarks[index][0] * frame_shape[1])
        y = int(self.landmarks[index][1] * frame_shape[0])
        return (x, y)


class FaceAnalyzer:
    """MediaPipe Face Mesh wrapper."""

    def __init__(self,
                 max_faces: int = config.MP_MAX_FACES,
                 detection_confidence: float = config.MP_DETECTION_CONFIDENCE,
                 tracking_confidence: float = config.MP_TRACKING_CONFIDENCE):
        self.max_faces = max_faces
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence

        # This project uses Face Mesh from the MediaPipe solutions API.
        if mp is None:
            raise ImportError("mediapipe is not installed")

        if not hasattr(mp, "solutions"):
            raise RuntimeError(
                "Incompatible mediapipe package. Install pinned deps with: "
                "pip install -r requirements.txt"
            )

        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=max_faces,
            refine_landmarks=True,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )

        self.results = None
        self.frame_count = 0

    def process(self, frame: np.ndarray) -> Optional[FaceData]:
        """
        Process frame and return face data.

        Args:
            frame: BGR image

        Returns:
            FaceData if face detected, None otherwise
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process
        self.results = self.face_mesh.process(rgb_frame)
        self.frame_count += 1

        if not self.results.multi_face_landmarks:
            return None

        # Get first face
        face_landmarks = self.results.multi_face_landmarks[0]

        # Extract 468 landmarks
        landmarks = []
        for landmark in face_landmarks.landmark:
            landmarks.append([landmark.x, landmark.y, landmark.z])

        landmarks = np.array(landmarks)

        # Calculate face bounding box (using landmarks range)
        x_coords = landmarks[:, 0]
        y_coords = landmarks[:, 1]
        x_min, x_max = np.min(x_coords), np.max(x_coords)
        y_min, y_max = np.min(y_coords), np.max(y_coords)
        bbox = (x_min, y_min, x_max - x_min, y_max - y_min)

        return FaceData(
            landmarks=landmarks,
            normalized_landmarks=landmarks.copy(),
            face_bbox=bbox,
            detection_confidence=1.0,  # MP doesn't give per-face confidence
            face_present=True,
            fps=0.0
        )

    def get_results(self):
        """Get raw MediaPipe results."""
        return self.results

    def release(self):
        """Release resources."""
        self.face_mesh.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


# Import cv2 for type hints


if __name__ == '__main__':
    print("Testing FaceAnalyzer...")

    # Test with camera
    cap = cv2.VideoCapture(0)
    analyzer = FaceAnalyzer()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        face_data = analyzer.process(frame)

        if face_data:
            # Draw simple face box
            h, w = frame.shape[:2]
            x, y, w_box, h_box = face_data.face_bbox
            x = int(x * w)
            y = int(y * h)
            w_box = int(w_box * w)
            h_box = int(h_box * h)
            cv2.rectangle(frame, (x, y), (x + w_box,
                          y + h_box), (0, 255, 0), 2)

            # Draw a few key landmarks
            for idx in [1, 33, 263, 0, 17]:  # nose, eyes, chin
                lm_x = int(face_data.landmarks[idx][0] * w)
                lm_y = int(face_data.landmarks[idx][1] * h)
                cv2.circle(frame, (lm_x, lm_y), 2, (0, 0, 255), -1)

        cv2.imshow("Face Test", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    analyzer.release()
    cv2.destroyAllWindows()
    print("Test complete.")
