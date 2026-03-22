"""Calibrator for 30-second driver signature learning."""

from enum import Enum
import numpy as np
from typing import Optional, List
from collections import deque
import time
from dataclasses import dataclass

from detectors import FaceAnalyzer
from calibration.driver_profile import DriverProfile
from utils.math_utils import calculate_iod
import config

# Debug flag - set to True to see calibration debug messages
DEBUG = True


class CalibrationStatus(Enum):
    """Calibration status states."""
    IDLE = "idle"
    WAITING = "waiting"
    COLLECTING = "collecting"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class CalibrationData:
    """Collected raw calibration data."""
    ear_values: List[float]
    iod_values: List[float]
    mar_values: List[float]
    yaw_values: List[float]
    pitch_values: List[float]
    roll_values: List[float]
    blink_times: List[float]


class Calibrator:
    """30-second calibration phase."""

    # Debug flag
    DEBUG = True

    def __init__(self, duration_sec: int = config.CALIBRATION_DURATION_SEC):
        self.duration_sec = duration_sec
        self.status = CalibrationStatus.IDLE

        # Data collection buffers
        self.ear_values: deque = deque(maxlen=900)  # 30 sec at 30fps
        self.iod_values: deque = deque(maxlen=900)
        self.yaw_values: deque = deque(maxlen=900)
        self.pitch_values: deque = deque(maxlen=900)
        self.roll_values: deque = deque(maxlen=900)
        # Bug fix: Added missing mar_values
        self.mar_values: deque = deque(maxlen=900)
        self.blink_times: List[float] = []

        # Timing
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        # Face detection during calibration
        self.face_analyzer = FaceAnalyzer()
        self.face_detected_frames = 0
        self.total_frames = 0

    def start(self) -> bool:
        """Start calibration process."""
        if self.status == CalibrationStatus.COLLECTING:
            return False

        self._reset_data()
        self.status = CalibrationStatus.WAITING
        self.start_time = time.time()
        print(
            f"[CALIB] Calibration started. Duration: {self.duration_sec} seconds")
        return True

    def _reset_data(self):
        """Reset all collection buffers."""
        self.ear_values.clear()
        self.iod_values.clear()
        self.yaw_values.clear()
        self.pitch_values.clear()
        self.roll_values.clear()
        self.blink_times.clear()
        self.face_detected_frames = 0
        self.total_frames = 0

    def process_frame(self, frame: np.ndarray,
                      eye_result=None, head_pose=None) -> tuple:
        """
        Process a frame during calibration.

        Returns:
            Tuple of (status, progress_0_to_1, time_remaining)
        """
        if self.status == CalibrationStatus.IDLE:
            return CalibrationStatus.IDLE, 0.0, 0

        self.total_frames += 1

        # Process face detection
        face_data = self.face_analyzer.process(frame)

        if face_data:
            self.face_detected_frames += 1

            # Collect IOD values to persist the average face scale.
            if face_data.landmarks is not None:
                iod = calculate_iod(face_data.landmarks)
                if iod > 0:
                    self.iod_values.append(iod)

            # Collect EAR values
            if eye_result and eye_result.avg_ear > 0:
                self.ear_values.append(eye_result.avg_ear)
                if eye_result.is_blinking:
                    self.blink_times.append(time.time())

            # Collect head pose values
            if head_pose:
                self.yaw_values.append(head_pose.yaw)
                self.pitch_values.append(head_pose.pitch)
                self.roll_values.append(head_pose.roll)

        # Debug output every 60 frames (~2 seconds)
        if self.DEBUG and self.total_frames % 60 == 0:
            face_rate = self.face_detected_frames / \
                max(1, self.total_frames) * 100
            print(f"[CALIB] Frame {self.total_frames}: EAR={len(self.ear_values)}, "
                  f"IOD={len(self.iod_values)}, MAR={len(self.mar_values)}, Face={face_rate:.1f}%")

        # Calculate progress
        elapsed = time.time() - self.start_time
        progress = min(elapsed / self.duration_sec, 1.0)
        time_remaining = max(0, int(self.duration_sec - elapsed))

        # Check completion
        if elapsed >= self.duration_sec:
            if self.status != CalibrationStatus.COMPLETE:
                if self.DEBUG:
                    print(f"[CALIB] Collection complete! EAR={len(self.ear_values)}, "
                          f"IOD={len(self.iod_values)}, MAR={len(self.mar_values)} samples collected")
                self.status = CalibrationStatus.PROCESSING
                self.end_time = time.time()

        if self.status == CalibrationStatus.PROCESSING:
            # Auto-complete after processing
            self.status = CalibrationStatus.COMPLETE

        return self.status, progress, time_remaining

    def generate_profile(self, driver_id: str = "default") -> Optional[DriverProfile]:
        """
        Generate driver profile from collected data.

        Returns:
            DriverProfile or None if insufficient data
        """
        if len(self.ear_values) < 30:
            print("[CALIB] ERROR: Insufficient EAR data for calibration "
                  f"(need 30, got {len(self.ear_values)})")
            self.status = CalibrationStatus.FAILED
            return None

        if len(self.mar_values) < 30:
            print("[CALIB] ERROR: Insufficient MAR data for calibration "
                  f"(need 30, got {len(self.mar_values)})")
            self.status = CalibrationStatus.FAILED
            return None

        # Face detection rate check - require > 80% for valid calibration
        face_detect_rate = self.face_detected_frames / \
            max(1, self.total_frames)
        if face_detect_rate < 0.80:
            print(
                f"[CALIB] ERROR: Insufficient face detection: {face_detect_rate:.1%} (need >= 80%)")
            self.status = CalibrationStatus.FAILED
            return None

        # Verify sufficient EAR samples (minimum 2.7 seconds of data)
        if len(self.ear_values) < 80:
            print(
                f"[CALIB] ERROR: Insufficient EAR samples: {len(self.ear_values)} (need >= 80)")
            self.status = CalibrationStatus.FAILED
            return None

        try:
            # Calculate statistics
            ear_array = np.array(list(self.ear_values))
            iod_array = np.array(list(self.iod_values))
            yaw_array = np.array(list(self.yaw_values))
            pitch_array = np.array(list(self.pitch_values))
            roll_array = np.array(list(self.roll_values))

            baseline_iod = float(np.mean(iod_array)) if len(
                iod_array) > 0 else 100.0

            # Create profile
            import datetime
            profile = DriverProfile(
                driver_id=driver_id,

                # Eye metrics
                ear_mean=float(np.mean(ear_array)),
                ear_std=float(np.std(ear_array)),
                ear_closed_threshold=float(
                    np.mean(ear_array) - 2 * np.std(ear_array)),
                baseline_iod=baseline_iod,
                blink_rate=len(self.blink_times),
                blink_duration=0.3,  # Default, can be improved

                # Head pose metrics
                yaw_center=float(np.mean(yaw_array)),
                yaw_std=float(np.std(yaw_array)),
                pitch_center=float(np.mean(pitch_array)),
                pitch_std=float(np.std(pitch_array)),
                roll_center=float(np.mean(roll_array)),
                roll_std=float(np.std(roll_array)),

                # Derived thresholds
                head_yaw_threshold=config.DEFAULT_HEAD_YAW_THRESHOLD,
                head_pitch_threshold=config.DEFAULT_HEAD_PITCH_THRESHOLD,

                # Status
                is_calibrated=True,
                calibration_date=datetime.datetime.now().isoformat()
            )

            if self.DEBUG:
                print(f"[CALIB] Profile generated successfully!")
                print(f"  EAR: mean={profile.ear_mean:.3f}, std={profile.ear_std:.3f}, "
                      f"closed_thresh={profile.ear_closed_threshold:.3f}, iod={profile.baseline_iod:.3f}")

            self.status = CalibrationStatus.COMPLETE
            return profile

        except Exception as e:
            print(f"[CALIB] ERROR: Calibration failed: {e}")
            self.status = CalibrationStatus.FAILED
            return None

    def is_complete(self) -> bool:
        """Check if calibration is complete."""
        return self.status == CalibrationStatus.COMPLETE

    def is_failed(self) -> bool:
        """Check if calibration failed."""
        return self.status == CalibrationStatus.FAILED

    def get_summary(self) -> dict:
        """Get calibration summary statistics."""
        return {
            'status': self.status.value,
            'duration': self.duration_sec,
            'frames_collected': len(self.ear_values),
            'face_detection_rate': (self.face_detected_frames /
                                    max(1, self.total_frames)),
            'ear_mean': float(np.mean(list(self.ear_values))) if self.ear_values else 0,
            'iod_mean': float(np.mean(list(self.iod_values))) if self.iod_values else 0,
            'mar_mean': float(np.mean(list(self.mar_values))) if self.mar_values else 0
        }

    def skip(self):
        """Skip calibration."""
        self.status = CalibrationStatus.FAILED

    def release(self):
        """Release resources."""
        self.face_analyzer.release()
