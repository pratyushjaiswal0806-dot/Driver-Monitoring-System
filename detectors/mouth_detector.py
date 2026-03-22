"""Mouth detection for yawning detection using MAR."""

import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import config
from utils.math_utils import calculate_mar, StateDurationTracker, TemporalSmoother


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

        # Temporal smoothing for MAR (reduces jitter sensitivity)
        self.mar_smoother = TemporalSmoother(alpha=config.SMOOTHING_ALPHA)

        # Yawn tracking
        self.yawn_tracker = StateDurationTracker(
            config.MOUTH_OPEN_ALERT_FRAMES)
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

        # Calculate MAR (raw)
        mar_indices = [config.MOUTH_TOP, config.MOUTH_BOTTOM,
                       config.MOUTH_LEFT, config.MOUTH_RIGHT]
        mar_raw = calculate_mar(landmarks, mar_indices)

        # Apply temporal smoothing to reduce jitter sensitivity
        mar = self.mar_smoother.update(mar_raw)

        # Store raw MAR for calibration
        if not self.calibrated:
            self.mar_history.append(mar_raw)
            if len(self.mar_history) > 100:
                self.mar_history = self.mar_history[-100:]

        # Calculate state-dependent thresholds with hysteresis
        # Threshold for mouth closing (lower threshold for exiting yawning state)
        yawn_end_threshold = self.baseline_mar * \
            1.2  # More aggressive closing threshold

        # Determine state based on smoothed MAR
        if mar < self.baseline_mar * 1.1:  # Mouth clearly closed
            state = MouthState.CLOSED
            is_open = False
        elif mar < self.yawn_threshold:  # Mouth slightly open (normal)
            state = MouthState.NORMAL
            is_open = True
        else:  # Mouth wide open (yawning)
            state = MouthState.YAWNING
            is_open = True

        # Track yawn duration - need to be above yawn threshold for consecutive frames
        # This triggers when threshold is first exceeded
        yawn_triggered = self.yawn_tracker.update(mar >= self.yawn_threshold)

        # Yawn state machine with proper transitions
        if yawn_triggered and not self.is_yawning:
            # Yawn just started (threshold exceeded for required frames)
            self.is_yawning = True
            self.yawn_count += 1
            if self.DEBUG:
                print(f"[MOUTH] Yawn #{self.yawn_count} started! MAR={mar:.3f} (raw={mar_raw:.3f}), "
                      f"threshold={self.yawn_threshold:.3f}")

        # Yawn ends only when mouth closes significantly (drops below lower threshold)
        # Not just when it drops below yawn threshold temporarily
        if self.is_yawning and mar < yawn_end_threshold:
            # Yawn ended (mouth closed)
            if self.DEBUG:
                print(f"[MOUTH] Yawn ended. Duration: {self.yawn_tracker.consecutive_frames/config.TARGET_FPS:.2f}s, "
                      f"MAR={mar:.3f} (raw={mar_raw:.3f})")
            self.is_yawning = False
            self.yawn_tracker.reset()

        # Calculate yawn duration in seconds
        yawn_duration = (self.yawn_tracker.consecutive_frames / config.TARGET_FPS
                         if self.yawn_tracker.consecutive_frames > 0 else 0.0)

        # Debug output
        if self.DEBUG and self.frame_count % self.DEBUG_INTERVAL == 0:
            yawn_end_threshold = self.baseline_mar * 1.2
            print(f"[MOUTH] MAR={mar:.3f} (raw={mar_raw:.3f}), state={state.value}, "
                  f"yawn_threshold={self.yawn_threshold:.3f}, "
                  f"baseline={self.baseline_mar:.3f}, yawn_end_threshold={yawn_end_threshold:.3f}")

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
        self.mar_smoother.reset()
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
