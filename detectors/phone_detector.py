"""Phone detection using YOLOv8."""

import numpy as np
from ultralytics import YOLO
from typing import List, Tuple, Optional
from dataclasses import dataclass
import time
import torch

import config


@dataclass
class Detection:
    """Single detection result."""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2


class PhoneDetector:
    """YOLOv8 phone detector with GPU optimization."""

    # Debug flag - set to True to see detection debug messages
    DEBUG = False

    def __init__(self,
                 model_path: str = config.YOLO_MODEL,
                 confidence: float = config.YOLO_CONFIDENCE):
        self.confidence = confidence
        self.last_detection_time = 0
        self.detection_cooldown = 0.1  # seconds between detections

        # State-based phone detection (require 2 consecutive detections)
        self.phone_detected_frames = 0
        self.phone_confirmation_threshold = 2  # frames needed to confirm
        self.last_best_detection = None  # Track last detection for grace period

        print(f"Loading YOLO model: {model_path}...")
        try:
            self.model = YOLO(model_path)

            # Optimize for GPU if available, fallback to CPU
            device = "0" if torch.cuda.is_available() else "cpu"
            if device == "0":
                print("[YOLO] GPU acceleration enabled (CUDA)")
            else:
                print("[YOLO] Running on CPU")

            # Run a dummy inference to load model into memory/GPU
            dummy = np.zeros((320, 320, 3), dtype=np.uint8)
            _ = self.model(dummy, verbose=False)

            print("YOLO model loaded successfully")
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            self.model = None

    def detect(self, frame: np.ndarray,
               face_bbox: Optional[Tuple] = None) -> List[Detection]:
        """
        Detect phones in frame.

        Args:
            frame: BGR image
            face_bbox: Optional face bounding box to check proximity

        Returns:
            List of detections
        """
        if self.model is None:
            return []

        # Rate limiting
        current_time = time.time()
        if current_time - self.last_detection_time < self.detection_cooldown:
            return []
        self.last_detection_time = current_time

        detections = []

        try:
            # Run YOLO inference
            results = self.model(frame, verbose=False)

            for result in results:
                if result.boxes is None:
                    continue

                for box in result.boxes:
                    conf = float(box.conf)
                    if conf < self.confidence:
                        continue

                    class_id = int(box.cls)
                    class_name = self.model.names[class_id]

                    # Filter for phone classes
                    if class_name not in config.YOLO_PHONE_CLASS_NAMES:
                        continue

                    if self.DEBUG:
                        print(
                            f"[PHONE] Found {class_name} (conf={conf:.2f}), checking proximity...")

                    # Get bbox coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    # Check proximity to face if face is detected
                    if face_bbox is not None:
                        if not self._check_proximity(
                            (x1, y1, x2, y2), face_bbox
                        ):
                            if self.DEBUG:
                                print(
                                    f"[PHONE] {class_name} too far from face, skipping")
                            continue  # Phone too far from face

                    if self.DEBUG:
                        print(f"[PHONE] Accepting detection: {class_name}")

                    detections.append(Detection(
                        class_id=class_id,
                        class_name=class_name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2)
                    ))

        except Exception as e:
            print(f"Detection error: {e}")

        return detections

    def _check_proximity(self, phone_bbox, face_bbox, max_distance_ratio=2.0) -> bool:
        """
        Check if phone is near face.

        Uses bbox distance. If phone is within max_distance_ratio of face size,
        consider it potentially being held by the driver.

        Args:
            phone_bbox: (x1, y1, x2, y2) in pixel coordinates
            face_bbox: (x1, y1, x2, y2) in pixel coordinates
        """
        if phone_bbox is None or face_bbox is None:
            return False

        # Both should be in pixel coordinates at this point
        # If face_bbox appears to be normalized (all values 0-1), skip proximity check
        # and conservatively return False
        if all(0 <= v <= 1 for v in face_bbox):
            return False

        # Calculate centers
        px = (phone_bbox[0] + phone_bbox[2]) / 2
        py = (phone_bbox[1] + phone_bbox[3]) / 2

        fx = (face_bbox[0] + face_bbox[2]) / 2
        fy = (face_bbox[1] + face_bbox[3]) / 2

        # Calculate distance
        distance = np.sqrt((px - fx) ** 2 + (py - fy) ** 2)

        # Face size reference
        face_size = max(face_bbox[2] - face_bbox[0],
                        face_bbox[3] - face_bbox[1])

        return distance < face_size * max_distance_ratio

    def is_phone_detected(self, frame: np.ndarray,
                          face_bbox: Optional[Tuple] = None) -> Tuple[bool, Optional[Detection]]:
        """
        Check if phone is detected with state-based consistency.
        Requires 2 consecutive detections to confirm, allows brief losses.

        Returns:
            Tuple of (detected, best_detection)
        """
        detections = self.detect(frame, face_bbox)

        if detections:
            # Found phone in this frame
            best_detection = max(detections, key=lambda d: d.confidence)
            self.last_best_detection = best_detection
            self.phone_detected_frames += 1

            if self.DEBUG:
                print(
                    f"[PHONE] Detection: {best_detection.class_name} (frames={self.phone_detected_frames})")

            # Confirm phone after 2 consecutive detections
            if self.phone_detected_frames >= self.phone_confirmation_threshold:
                if self.DEBUG:
                    print(f"[PHONE] CONFIRMED detected!")
                return True, best_detection
        else:
            # No phone in this frame - allow grace period
            if self.phone_detected_frames > 0:
                self.phone_detected_frames -= 1
                if self.phone_detected_frames >= self.phone_confirmation_threshold:
                    if self.DEBUG:
                        print(
                            f"[PHONE] Still detected (grace period, frames={self.phone_detected_frames})")
                    return True, self.last_best_detection
            # Reset if grace period expires
            self.phone_detected_frames = 0

        return False, self.last_best_detection if self.phone_detected_frames > 0 else None

    def reset(self):
        """Reset detector state."""
        self.last_detection_time = 0
