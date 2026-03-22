"""Eye detection using Eye Aspect Ratio (EAR)."""

import numpy as np
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import time

from utils.math_utils import calculate_normalized_ear, StateDurationTracker
import config


class EyeState(Enum):
    """Eye state classifications."""
    OPEN = "open"
    CLOSED = "closed"
    DROWSY = "drowsy"
    UNKNOWN = "unknown"


@dataclass
class EyeResult:
    """Result from eye detection."""
    left_ear: float
    right_ear: float
    avg_ear: float
    state: EyeState
    is_blinking: bool
    eyes_closed_duration: float  # seconds
    blink_count: int


class EyeDetector:
    """Detect eye state using EAR with calibrated thresholds."""

    def __init__(self,
                 ear_threshold: float = None,
                 ear_closed_threshold: float = None):
        # Use calibrated thresholds or defaults
        self.ear_threshold = ear_threshold or config.DEFAULT_EAR_THRESHOLD
        self.ear_closed_threshold = ear_closed_threshold or config.DEFAULT_EAR_CLOSED_THRESHOLD

        # State tracking
        self.closed_tracker = StateDurationTracker(
            config.EYES_CLOSED_ALERT_FRAMES)
        self.blink_tracker = StateDurationTracker(config.BLINK_MIN_FRAMES)

        # Blink counting
        self.blink_count = 0
        self.last_blink_time = time.time()
        self.blink_history = []

        # Eye closure timing
        self.eyes_closed_start: Optional[float] = None
        self.max_eyes_closed_duration = 0.0

        # EAR history for calibration
        self.ear_history = []
        self.baseline_ear: Optional[float] = None
        self.calibrated = False

        # Previous state for blink detection
        self.prev_state = EyeState.UNKNOWN
        self.blink_in_progress = False

    def detect(self, landmarks: np.ndarray, driver_profile=None) -> EyeResult:
        """
        Detect eye state from face landmarks.

        Args:
            landmarks: 468 face landmarks from MediaPipe
            driver_profile: Optional calibrated driver profile

        Returns:
            EyeResult with state and metrics
        """
        # Use driver's personal thresholds if calibrated
        reference_iod = None
        if driver_profile and driver_profile.is_calibrated:
            self.ear_threshold = driver_profile.ear_closed_threshold
            self.calibrated = True
            self.baseline_ear = driver_profile.ear_mean
            reference_iod = getattr(driver_profile, 'baseline_iod', None)
            if reference_iod is not None and reference_iod <= 0:
                reference_iod = None

        # Calculate scale-stable EAR for both eyes
        left_ear = calculate_normalized_ear(
            landmarks, config.LEFT_EYE_INDICES, reference_iod=reference_iod)
        right_ear = calculate_normalized_ear(
            landmarks, config.RIGHT_EYE_INDICES, reference_iod=reference_iod)
        avg_ear = (left_ear + right_ear) / 2.0

        # Store for calibration
        if not self.calibrated:
            self.ear_history.append(avg_ear)
            if len(self.ear_history) > 100:
                self.ear_history = self.ear_history[-100:]

        # Determine eye state
        if avg_ear < self.ear_closed_threshold:
            state = EyeState.CLOSED
            is_closed = True
        elif avg_ear < self.ear_threshold:
            # Bug fix: Was incorrectly setting to CLOSED. Now properly transitions through thresholds
            state = EyeState.OPEN  # In threshold zone but not fully closed
            is_closed = False
        else:
            state = EyeState.OPEN
            is_closed = False

        # Track duration (for drowsiness detection)
        alert_triggered = self.closed_tracker.update(is_closed)

        # Calculate closure duration
        if is_closed:
            if self.eyes_closed_start is None:
                self.eyes_closed_start = time.time()
            eyes_closed_duration = time.time() - self.eyes_closed_start
        else:
            if self.eyes_closed_start is not None:
                duration = time.time() - self.eyes_closed_start
                if duration > self.max_eyes_closed_duration:
                    self.max_eyes_closed_duration = duration
                self.eyes_closed_start = None
            eyes_closed_duration = 0.0

        # Update to DROWSY if closed too long
        if alert_triggered:
            state = EyeState.DROWSY

        # Blink detection (quick close-open cycle)
        is_blinking = self._detect_blink(state)

        return EyeResult(
            left_ear=left_ear,
            right_ear=right_ear,
            avg_ear=avg_ear,
            state=state,
            is_blinking=is_blinking,
            blink_count=self.blink_count,
            eyes_closed_duration=eyes_closed_duration
        )

    def _detect_blink(self, current_state: EyeState) -> bool:
        """Detect a complete blink (closed then opened quickly)."""
        blink_detected = False

        # Blink transition: open -> closed -> open
        if self.prev_state == EyeState.OPEN and current_state == EyeState.CLOSED:
            # Potential blink started
            self.blink_in_progress = True

        elif self.prev_state == EyeState.CLOSED and current_state == EyeState.OPEN:
            if self.blink_in_progress:
                # Blink completed
                self.blink_count += 1
                self.blink_in_progress = False
                self.last_blink_time = time.time()
                blink_detected = True

                # Record blink in history
                self.blink_history.append(time.time())
                # Keep last 60 seconds of blink history
                cutoff = time.time() - 60
                self.blink_history = [
                    b for b in self.blink_history if b > cutoff]

        self.prev_state = current_state

        # Clear blink flag if eyes closed too long (becomes drowsy, not blink)
        if self.blink_in_progress and self.closed_tracker.consecutive_frames > config.BLINK_MAX_FRAMES:
            self.blink_in_progress = False

        return blink_detected

    def get_blink_rate(self) -> float:
        """Get blink rate (blinks per minute)."""
        recent_blinks = len(self.blink_history)
        # Bug fix: Normalize to per-minute (blinks in last 60s * 60 / 60 = just count)
        # But since history is already filtered to last 60s, we need to scale appropriately
        if not self.blink_history:
            return 0.0
        # Calculate actual time span covered by blink history
        if len(self.blink_history) < 2:
            return 0.0
        time_span = self.blink_history[-1] - self.blink_history[0]
        if time_span < 1.0:
            return 0.0
        # Blinks per minute
        return (recent_blinks / time_span) * 60.0

    def calibrate(self, driver_profile=None) -> dict:
        """
        Calculate calibration from collected EAR history.

        Returns:
            Dictionary with calibration metrics
        """
        if len(self.ear_history) < 30:
            return {}

        ear_array = np.array(self.ear_history)
        ear_mean = float(np.mean(ear_array))
        ear_std = float(np.std(ear_array))

        # Set dynamic thresholds
        self.baseline_ear = ear_mean
        self.ear_closed_threshold = ear_mean - 2 * ear_std
        self.calibrated = True

        return {
            'ear_mean': ear_mean,
            'ear_std': ear_std,
            'ear_threshold': self.ear_threshold,
            'ear_closed_threshold': self.ear_closed_threshold
        }

    def reset(self):
        """Reset detector state."""
        self.closed_tracker.reset()
        self.blink_count = 0
        self.blink_history.clear()
        self.eyes_closed_start = None
        self.blink_in_progress = False
        self.prev_state = EyeState.UNKNOWN
        self.ear_history.clear()

    def get_calibration_data(self) -> dict:
        """Get current calibration data."""
        return {
            'baseline_ear': self.baseline_ear,
            'ear_threshold': self.ear_threshold,
            'ear_closed_threshold': self.ear_closed_threshold,
            'calibrated': self.calibrated,
            'history_samples': len(self.ear_history)
        }
