"""Head pose estimation using solvePnP."""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

import config
from utils.math_utils import StateDurationTracker


class HeadDirection(Enum):
    """Head direction classifications."""
    FRONT = "front"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class HeadPose:
    """Head pose angles."""
    yaw: float      # Left/Right rotation (degrees)
    pitch: float    # Up/Down rotation (degrees)
    roll: float     # Tilt rotation (degrees)
    direction: HeadDirection
    looking_away: bool
    away_duration: float  # seconds


class HeadPoseEstimator:
    """Estimate head orientation using MediaPipe landmarks."""

    # 3D model points (generic face model)
    # These are approximate positions for the facial features
    MODEL_POINTS = np.array([
        (0.0, 0.0, 0.0),          # Nose tip
        (0.0, -330.0, -65.0),      # Chin
        (-225.0, 170.0, -135.0),   # Left eye left corner
        (225.0, 170.0, -135.0),    # Right eye right corner
        (-150.0, -150.0, -125.0),  # Left mouth corner
        (150.0, -150.0, -125.0)    # Right mouth corner
    ], dtype=np.float64)

    def __init__(self, yaw_threshold: float = None, pitch_threshold: float = None):
        # Thresholds (in degrees)
        self.yaw_threshold = yaw_threshold or config.DEFAULT_HEAD_YAW_THRESHOLD
        self.pitch_threshold = pitch_threshold or config.DEFAULT_HEAD_PITCH_THRESHOLD

        self.baseline_yaw: float = 0.0
        self.baseline_pitch: float = 0.0
        self.calibrated = False

        # Camera matrix
        self.camera_matrix = None
        self.dist_coeffs = None

        # State tracking
        self.away_tracker = StateDurationTracker(config.HEAD_AWAY_ALERT_FRAMES)

        # History for calibration
        self.yaw_history = []
        self.pitch_history = []

    def _get_camera_matrix(self, frame_shape):
        """Initialize camera matrix from frame dimensions."""
        if self.camera_matrix is not None:
            return

        size = frame_shape[1], frame_shape[0]  # width, height
        focal_length = size[0]
        center = (size[0] / 2, size[1] / 2)

        self.camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)

        self.dist_coeffs = np.zeros((4, 1))

    def _get_image_points(self, landmarks: np.ndarray, frame_shape) -> Optional[np.ndarray]:
        """Extract 2D image points from landmarks with validation."""
        h, w = frame_shape[:2]
        image_points = []

        for idx in config.FACE_MODEL_POINTS:
            # Bug fix: Validate landmark exists with proper NaN check
            # MediaPipe returns normalized (0-1) coordinates, so 0 is valid
            if idx >= len(landmarks):
                return None  # Index out of bounds

            x = landmarks[idx][0]
            y = landmarks[idx][1]

            # Check for NaN or out-of-bounds (< -0.1 or > 1.1 to account for rounding)
            if np.isnan(x) or np.isnan(y) or x < -0.1 or x > 1.1 or y < -0.1 or y > 1.1:
                return None  # Invalid landmark

            image_points.append([x * w, y * h])

        return np.array(image_points, dtype=np.float64)

    def estimate(self, landmarks: np.ndarray, frame_shape: tuple,
                 driver_profile=None) -> Optional[HeadPose]:
        """
        Estimate head pose from landmarks.

        Args:
            landmarks: 468 face landmarks
            frame_shape: (h, w) of frame
            driver_profile: Optional calibrated driver profile

        Returns:
            HeadPose with angles
        """
        self._get_camera_matrix(frame_shape)

        if driver_profile and driver_profile.is_calibrated:
            self.baseline_yaw = driver_profile.yaw_center
            self.baseline_pitch = driver_profile.pitch_center
            self.calibrated = True

        # Get image points with validation
        image_points = self._get_image_points(landmarks, frame_shape)
        if image_points is None:
            return None  # Skip frame due to invalid landmarks

        try:
            # Solve PnP
            success, rotation_vec, translation_vec = cv2.solvePnP(
                self.MODEL_POINTS,
                image_points,
                self.camera_matrix,
                self.dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if not success:
                return None

            # Convert rotation vector to rotation matrix
            rotation_mat, _ = cv2.Rodrigues(rotation_vec)

            # Calculate Euler angles
            yaw, pitch, roll = self._rotation_matrix_to_euler_angles(
                rotation_mat)

            # Store for calibration
            if not self.calibrated:
                self.yaw_history.append(yaw)
                self.pitch_history.append(pitch)
                if len(self.yaw_history) > 100:
                    self.yaw_history = self.yaw_history[-100:]
                    self.pitch_history = self.pitch_history[-100:]

            # Determine direction
            direction, looking_away = self._classify_direction(yaw, pitch)

            # Track "looking away" state
            alert_triggered = self.away_tracker.update(looking_away)

            # Calculate away duration
            away_duration = (self.away_tracker.consecutive_frames / config.TARGET_FPS
                             if self.away_tracker.consecutive_frames > 0 else 0.0)

            return HeadPose(
                yaw=yaw,
                pitch=pitch,
                roll=roll,
                direction=direction,
                looking_away=looking_away,
                away_duration=away_duration
            )

        except Exception as e:
            return None

    def _rotation_matrix_to_euler_angles(self, R: np.ndarray) -> Tuple[float, float, float]:
        """Convert rotation matrix to Euler angles (yaw, pitch, roll)."""
        # Simplified calculation for head pose
        sy = np.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])

        singular = sy < 1e-6

        if not singular:
            x = np.arctan2(R[2, 1], R[2, 2])
            y = np.arctan2(-R[2, 0], sy)
            z = np.arctan2(R[1, 0], R[0, 0])
        else:
            x = np.arctan2(-R[1, 2], R[1, 1])
            y = np.arctan2(-R[2, 0], sy)
            z = 0

        # Convert to degrees and adjust
        yaw = np.degrees(z)   # Left/Right
        pitch = np.degrees(y)  # Up/Down
        roll = np.degrees(x)   # Tilt

        return yaw, pitch, roll

    def _classify_direction(self, yaw: float, pitch: float) -> Tuple[HeadDirection, bool]:
        """Classify head direction and check if looking away."""
        # Calculate deviation from baseline
        yaw_deviation = abs(yaw - self.baseline_yaw)
        pitch_deviation = abs(pitch - self.baseline_pitch)

        # Front-facing when both deviations are inside thresholds.
        if yaw_deviation <= self.yaw_threshold and pitch_deviation <= self.pitch_threshold:
            return HeadDirection.FRONT, False

        # Otherwise classify by the dominant axis so the display is consistent.
        if yaw_deviation >= pitch_deviation and yaw_deviation > self.yaw_threshold:
            direction = HeadDirection.LEFT if yaw < self.baseline_yaw else HeadDirection.RIGHT
            return direction, True

        if pitch_deviation > self.pitch_threshold:
            direction = HeadDirection.DOWN if pitch > self.baseline_pitch else HeadDirection.UP
            return direction, True

        return HeadDirection.FRONT, False

    def calibrate(self) -> dict:
        """Calculate calibration from collected pose history."""
        if len(self.yaw_history) < 30:
            return {}

        yaw_array = np.array(self.yaw_history)
        pitch_array = np.array(self.pitch_history)

        self.baseline_yaw = float(np.mean(yaw_array))
        self.baseline_pitch = float(np.mean(pitch_array))

        yaw_std = float(np.std(yaw_array))
        pitch_std = float(np.std(pitch_array))

        self.calibrated = True

        return {
            'yaw_center': self.baseline_yaw,
            'pitch_center': self.baseline_pitch,
            'yaw_std': yaw_std,
            'pitch_std': pitch_std,
            'yaw_threshold': self.yaw_threshold,
            'pitch_threshold': self.pitch_threshold
        }

    def reset(self):
        """Reset state."""
        self.away_tracker.reset()
        self.yaw_history.clear()
        self.pitch_history.clear()
        self.calibrated = False

    def get_calibration_data(self) -> dict:
        """Get calibration data."""
        return {
            'baseline_yaw': self.baseline_yaw,
            'baseline_pitch': self.baseline_pitch,
            'calibrated': self.calibrated,
            'thresholds': (self.yaw_threshold, self.pitch_threshold)
        }
