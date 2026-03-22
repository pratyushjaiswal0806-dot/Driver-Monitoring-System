"""Mathematical utilities for detection calculations."""

import numpy as np
from typing import List, Tuple, Optional
from collections import deque

REFERENCE_IOD = 100.0


def euclidean_distance(p1: np.ndarray, p2: np.ndarray) -> float:
    """Calculate Euclidean distance between two points."""
    return np.linalg.norm(p1 - p2)


def calculate_iod(landmarks: np.ndarray) -> float:
    """
    Calculate the inter-ocular distance (IOD).

    The IOD is the Euclidean distance between MediaPipe landmark 33
    (left eye outer corner) and landmark 263 (right eye outer corner).

    Args:
        landmarks: Face mesh landmarks in normalized or pixel coordinates.

    Returns:
        Inter-ocular distance, or 1.0 if the value is invalid or zero.
    """
    if landmarks is None or len(landmarks) <= 263:
        return 1.0

    left_outer = np.asarray(landmarks[33], dtype=float)
    right_outer = np.asarray(landmarks[263], dtype=float)
    iod = float(np.linalg.norm(left_outer - right_outer))

    if iod <= 1e-6:
        return 1.0

    return iod


def calculate_ear(landmarks: np.ndarray, eye_indices: List[int]) -> float:
    """
    Calculate Eye Aspect Ratio (EAR).

    EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)

    Where points are:
        p1 ----- p4
        |  \   /  |
        p2  p3  p5
           |  |
           p6

    Args:
        landmarks: Face mesh landmarks (468 points)
        eye_indices: 6 indices for the eye [p1, p2, p3, p4, p5, p6]

    Returns:
        Eye Aspect Ratio (0.0 to ~0.5)
    """
    if len(eye_indices) != 6:
        raise ValueError("eye_indices must contain exactly 6 points")

    # Bug fix: Validate landmark indices before access
    if any(i >= len(landmarks) for i in eye_indices):
        return 0.0  # Invalid index

    # Get points
    p = [landmarks[i] for i in eye_indices]

    # Calculate distances
    vertical_1 = euclidean_distance(p[1], p[5])  # ||p2-p6||
    vertical_2 = euclidean_distance(p[2], p[4])  # ||p3-p5||
    horizontal = euclidean_distance(p[0], p[3])    # ||p1-p4||

    if horizontal < 1e-6:
        return 0.0

    ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
    return float(ear)


def calculate_normalized_ear(
    landmarks: np.ndarray,
    eye_indices: Optional[List[int]] = None,
    reference_iod: Optional[float] = None,
) -> float:
    """
    Calculate a scale-stable EAR value using the inter-ocular distance.

    EAR is already a ratio, so it is dimensionless. By default the function
    returns the raw EAR so existing callers keep the same behavior. When a
    `reference_iod` is provided, the result is adjusted against the current
    inter-ocular distance to support personalized normalization.

    Args:
        landmarks: Face mesh landmarks.
        eye_indices: Optional 6-point eye index list for one eye.
        reference_iod: Optional reference IOD used for personalized scaling.

    Returns:
        Scale-stable EAR value.
    """
    current_iod = calculate_iod(landmarks)
    if current_iod is None or current_iod <= 0:
        current_iod = 1.0

    if eye_indices is not None:
        raw_ear = float(calculate_ear(landmarks, eye_indices))
        if reference_iod is None:
            return raw_ear
        return float(raw_ear * (reference_iod / current_iod))

    try:
        import config

        left_ear = calculate_ear(landmarks, config.LEFT_EYE_INDICES)
        right_ear = calculate_ear(landmarks, config.RIGHT_EYE_INDICES)
        raw_ear = float((left_ear + right_ear) / 2.0)
        if reference_iod is None:
            return raw_ear
        return float(raw_ear * (reference_iod / current_iod))
    except Exception:
        return 0.0


def calculate_mar(landmarks: np.ndarray, mar_indices: List[int]) -> float:
    """
    Calculate Mouth Aspect Ratio (MAR).

    MAR = (upper_lip - lower_lip) / mouth_width

    Args:
        landmarks: Face mesh landmarks (468 points)
        mar_indices: [top_lip, bottom_lip, left_corner, right_corner]

    Returns:
        Mouth Aspect Ratio
    """
    if len(mar_indices) != 4:
        raise ValueError("mar_indices must contain exactly 4 points")

    top = landmarks[mar_indices[0]]
    bottom = landmarks[mar_indices[1]]
    left = landmarks[mar_indices[2]]
    right = landmarks[mar_indices[3]]

    vertical = euclidean_distance(top, bottom)
    horizontal = euclidean_distance(left, right)

    if horizontal < 1e-6:
        return 0.0

    mar = vertical / horizontal
    return float(mar)


def ewma(current_value: float, previous_value: float, alpha: float = 0.3) -> float:
    """
    Exponentially Weighted Moving Average for temporal smoothing.

    smoothed = alpha * current + (1 - alpha) * previous

    Args:
        current_value: Current measurement
        previous_value: Previous smoothed value
        alpha: Smoothing factor (0-1), higher = more responsive

    Returns:
        Smoothed value
    """
    return alpha * current_value + (1 - alpha) * previous_value


class TemporalSmoother:
    """Temporal smoothing using EWMA."""

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self.value = None
        self.initialized = False

    def update(self, new_value: float) -> float:
        """Update with new value and return smoothed result."""
        if not self.initialized:
            self.value = new_value
            self.initialized = True
        else:
            self.value = ewma(new_value, self.value, self.alpha)
        return self.value

    def reset(self):
        """Reset the smoother."""
        self.value = None
        self.initialized = False


class StateDurationTracker:
    """Track how long a state has been active with hysteresis."""

    def __init__(self, threshold_frames: int = 30, hysteresis_frames: int = 5):
        self.threshold_frames = threshold_frames         # Frames to trigger alert
        # Frames to clear alert after release
        self.hysteresis_frames = hysteresis_frames
        self.consecutive_frames = 0
        self.triggered = False

    def update(self, current_state: bool) -> bool:
        """
        Update with current state using hysteresis to prevent flicker.

        Returns:
            True if state has persisted for threshold duration
        """
        if current_state:
            # State is active: increment frame counter
            self.consecutive_frames += 1

            # Trigger alert when threshold reached
            if not self.triggered and self.consecutive_frames >= self.threshold_frames:
                self.triggered = True
                return True

            return self.triggered
        else:
            # State is inactive: apply hysteresis
            if self.triggered:
                # Still in triggered state, apply exit hysteresis
                self.consecutive_frames = max(
                    0, self.consecutive_frames - self.hysteresis_frames)

                # Clear triggered state after hysteresis elapses
                if self.consecutive_frames <= 0:
                    self.triggered = False
                    self.consecutive_frames = 0
            else:
                # Not triggered, reset counter immediately
                self.consecutive_frames = 0

            return self.triggered

    def reset(self):
        """Reset the tracker."""
        self.consecutive_frames = 0
        self.triggered = False

    def get_duration(self, fps: float = 30.0) -> float:
        """Get duration in seconds."""
        return self.consecutive_frames / fps


def calculate_iou(box1: Tuple[float, float, float, float],
                  box2: Tuple[float, float, float, float]) -> float:
    """
    Calculate Intersection over Union (IoU) of two bounding boxes.

    Args:
        box1: (x1, y1, x2, y2) - top-left and bottom-right corners
        box2: (x1, y1, x2, y2)

    Returns:
        IoU value between 0 and 1
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    # Calculate intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)

    if x2_i <= x1_i or y2_i <= y1_i:
        return 0.0

    intersection = (x2_i - x1_i) * (y2_i - y1_i)

    # Calculate areas
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)

    union = area1 + area2 - intersection

    if union < 1e-6:
        return 0.0

    return intersection / union


def normalize_value(value: float,
                    min_val: float,
                    max_val: float,
                    clip: bool = True) -> float:
    """
    Normalize a value to 0-1 range.

    Args:
        value: Input value
        min_val: Minimum expected value
        max_val: Maximum expected value
        clip: Whether to clip to [0, 1]

    Returns:
        Normalized value
    """
    if max_val - min_val < 1e-6:
        return 0.5

    normalized = (value - min_val) / (max_val - min_val)

    if clip:
        normalized = max(0.0, min(1.0, normalized))

    return normalized


def calculate_head_pose_angles(rotation_vec: np.ndarray) -> Tuple[float, float, float]:
    """
    Convert rotation vector to Euler angles (yaw, pitch, roll).

    Args:
        rotation_vec: 3x1 rotation vector from solvePnP

    Returns:
        Tuple of (yaw, pitch, roll) in degrees
    """
    # Convert rotation vector to rotation matrix
    from cv2 import Rodrigues
    rotation_mat, _ = Rodrigues(rotation_vec)

    # Calculate Euler angles
    # Correct approach for head pose estimation
    yaw = np.arctan2(rotation_mat[1, 0], rotation_mat[0, 0])
    pitch = np.arcsin(-rotation_mat[2, 0])
    roll = np.arctan2(rotation_mat[2, 1], rotation_mat[2, 2])

    # Convert to degrees
    yaw_deg = np.degrees(yaw)
    pitch_deg = np.degrees(pitch)
    roll_deg = np.degrees(roll)

    return float(yaw_deg), float(pitch_deg), float(roll_deg)


def calculate_baseline_stats(values: List[float]) -> Tuple[float, float]:
    """
    Calculate mean and std for baseline metrics.

    Args:
        values: List of measurements during calibration

    Returns:
        Tuple of (mean, std)
    """
    if len(values) < 2:
        return values[0] if values else 0.0, 0.0

    arr = np.array(values)
    return float(np.mean(arr)), float(np.std(arr))


class RingBuffer:
    """Fixed-size circular buffer for temporal data."""

    def __init__(self, size: int = 300):
        self.size = size
        self.buffer = deque(maxlen=size)

    def append(self, value):
        """Add value to buffer."""
        self.buffer.append(value)

    def get(self) -> np.ndarray:
        """Get buffer contents as array."""
        return np.array(self.buffer)

    def mean(self) -> float:
        """Calculate mean."""
        if len(self.buffer) == 0:
            return 0.0
        return float(np.mean(self.buffer))

    def std(self) -> float:
        """Calculate standard deviation."""
        if len(self.buffer) < 2:
            return 0.0
        return float(np.std(self.buffer))

    def clear(self):
        """Clear buffer."""
        self.buffer.clear()

    def is_full(self) -> bool:
        """Check if buffer is full."""
        return len(self.buffer) == self.size

    def __len__(self):
        return len(self.buffer)
