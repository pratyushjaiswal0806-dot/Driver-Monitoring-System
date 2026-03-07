"""Mouth detection for yawning detection using MAR."""

import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import config
from utils.math_utils import calculate_mar, StateDurationTracker


class MouthState(Enum):
    """Mouth state classifications."""
    CLOSED = "closed"
    NORMAL = "normal"
    YAWNING = "yawning"
    UNKNOWN = "unknown"


@dataclass
class MouthResult:
    """Result from mouth detection."""
    mar: float  # Mouth Aspect Ratio
    state: MouthState  # Current state
    is_yawning: bool  # Yawning detected
    yawn_duration: float  # Yawn duration in seconds
    yawn_count: int  # Total yawns detected


class MouthDetector:
    """Detect mouth state using MAR with yawning detection."""

    # Debug flag - set to True to see MAR debug messages
    DEBUG = True
    DEBUG_INTERVAL = 30  # Print every 30 frames to avoid spam

    def __init__(self,
                 mar_threshold: float = None,
                 yawn_threshold: float = None):
        # Thresholds
        self.mar_threshold = mar_threshold or config.DEFAULT_MAR_THRESHOLD
        self.yawn_threshold = yawn_threshold or config.DEFAULT_MAR_YAWN_THRESHOLD

        self.baseline_mar: float = self.mar_threshold
        self.calibrated = False

        # Yawn tracking
        self.yawn_tracker = StateDurationTracker(config.MOUTH_OPEN_ALERT_FRAMES)
        self.is_yawning = False
        self.yawn_count = 0
        self.yawn_start_time = None

        # MAR history for calibration
        self.mar_history = []

        # Debug counters
        self.frame_count = 0

    def detect(self, landmarks: np.ndarray, driver_profile=None) -> MouthResult:
        """
        Detect mouth state from face landmarks.

        Args:
            landmarks: 468 face landmarks from MediaPipe
            driver_profile: Optional calibrated driver profile

        Returns:
            MouthResult with state and metrics
        """
        self.frame_count += 1

        # Use driver's personal thresholds if available
        if driver_profile and driver_profile.is_calibrated:
            self.baseline_mar = driver_profile.mar_mean
            self.yawn_threshold = driver_profile.mar_yawn_threshold
            self.calibrated = True

        # Calculate MAR
        mar_indices = [config.MOUTH_TOP, config.MOUTH_BOTTOM,
                       config.MOUTH_LEFT, config.MOUTH_RIGHT]
        mar = calculate_mar(landmarks, mar_indices)

        # Store for calibration
        if not self.calibrated:
            self.mar_history.append(mar)
            if len(self.mar_history) > 100:
                self.mar_history = self.mar_history[-100:]

        # Calculate thresholds based on baseline
        close_threshold = self.baseline_mar * 1.2
        yawn_end_threshold = self.baseline_mar * 1.3

        # Determine state
        if mar < close_threshold:  # Closed/normal
            state = MouthState.CLOSED
            is_open = False
        elif mar < self.yawn_threshold:
            state = MouthState.NORMAL  # Slightly open
            is_open = True
        else:
            state = MouthState.YAWNING  # Wide open (yawn)
            is_open = True

        # Track yawn duration - need to be above yawn threshold for consecutive frames
        yawn_triggered = self.yawn_tracker.update(is_open and mar >= self.yawn_threshold)

        # Count yawns
        was_yawning = self.is_yawning
        if yawn_triggered and not self.is_yawning:
            # Yawn started
            self.is_yawning = True
            self.yawn_count += 1
            if self.DEBUG:
                print(f"[MOUTH] Yawn #{self.yawn_count} started! MAR={mar:.3f}, threshold={self.yawn_threshold:.3f}")

        if not is_open or mar < yawn_end_threshold:
            # Yawn ended
            if self.is_yawning:
                if self.DEBUG:
                    print(f"[MOUTH] Yawn ended. Duration: {self.yawn_tracker.consecutive_frames/config.TARGET_FPS:.2f}s")
            self.is_yawning = False

        # Calculate yawn duration in seconds
        yawn_duration = (self.yawn_tracker.consecutive_frames / config.TARGET_FPS
                         if self.yawn_tracker.consecutive_frames > 0 else 0.0)

        # Debug output
        if self.DEBUG and self.frame_count % self.DEBUG_INTERVAL == 0:
            print(f"[MOUTH] MAR={mar:.3f}, state={state.value}, threshold={self.yawn_threshold:.3f}, "
                  f"baseline={self.baseline_mar:.3f}, close_thresh={close_threshold:.3f}")

        return MouthResult(
            mar=mar,
            state=state,
            is_yawning=self.is_yawning,
            yawn_duration=yawn_duration,
            yawn_count=self.yawn_count
        )

    def calibrate(self) -> dict:
        """
        Calculate calibration from collected MAR history.

        Returns:
            Dictionary with calibration metrics
        """
        if len(self.mar_history) < 30:
            return {}

        mar_array = np.array(self.mar_history)
        mar_mean = float(np.mean(mar_array))
        mar_std = float(np.std(mar_array))

        # Set dynamic thresholds
        self.baseline_mar = mar_mean
        self.yawn_threshold = mar_mean + 2.5 * mar_std  # Yawn when significantly open
        self.calibrated = True

        if self.DEBUG:
            print(f"[MOUTH] Calibrated: mean={mar_mean:.3f}, std={mar_std:.3f}, "
                  f"yawn_threshold={self.yawn_threshold:.3f}")

        return {
            'mar_mean': mar_mean,
            'mar_std': mar_std,
            'mar_threshold': self.mar_threshold,
            'mar_yawn_threshold': self.yawn_threshold
        }

    def reset(self):
        """Reset detector state."""
        self.yawn_tracker.reset()
        self.is_yawning = False
        self.yawn_count = 0
        self.mar_history.clear()
        self.calibrated = False
        self.frame_count = 0

    def get_calibration_data(self) -> dict:
        """Get current calibration data."""
        return {
            'baseline_mar': self.baseline_mar,
            'yawn_threshold': self.yawn_threshold,
            'calibrated': self.calibrated,
            'history_samples': len(self.mar_history)
        }