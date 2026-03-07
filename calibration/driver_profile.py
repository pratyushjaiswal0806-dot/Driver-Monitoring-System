"""Driver profile for storing personal baselines."""

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional
import numpy as np
import config


@dataclass
class DriverProfile:
    """Driver's personal baseline measurements."""

    # Identification
    driver_id: str = "default"

    # Eye measurements
    ear_mean: float = config.DEFAULT_EAR_THRESHOLD
    ear_std: float = 0.02
    ear_closed_threshold: float = config.DEFAULT_EAR_CLOSED_THRESHOLD
    blink_rate: float = 15.0       # Blinks per minute
    blink_duration: float = 0.3    # Average blink duration in seconds

    # Mouth measurements
    mar_mean: float = config.DEFAULT_MAR_THRESHOLD
    mar_std: float = 0.03
    mar_yawn_threshold: float = config.DEFAULT_MAR_YAWN_THRESHOLD

    # Head pose measurements
    yaw_center: float = 0.0        # Center position (degrees)
    yaw_std: float = 5.0
    pitch_center: float = 0.0
    pitch_std: float = 5.0
    roll_center: float = 0.0
    roll_std: float = 5.0

    # Derived thresholds
    head_yaw_threshold: float = config.DEFAULT_HEAD_YAW_THRESHOLD
    head_pitch_threshold: float = config.DEFAULT_HEAD_PITCH_THRESHOLD

    # Status
    is_calibrated: bool = False
    calibration_date: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'DriverProfile':
        """Create profile from dictionary."""
        # Filter to only valid fields
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

    def to_dict(self) -> dict:
        """Convert profile to dictionary."""
        return asdict(self)

    def save(self, filepath: str = None) -> bool:
        """Save profile to JSON file."""
        if filepath is None:
            filepath = os.path.join(config.PROFILE_DIR, f"{self.driver_id}.json")

        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving profile: {e}")
            return False

    @classmethod
    def load(cls, driver_id: str = None, filepath: str = None) -> Optional['DriverProfile']:
        """Load profile from JSON file."""
        if filepath is None:
            if driver_id is None:
                driver_id = config.DEFAULT_PROFILE_NAME
            filepath = os.path.join(config.PROFILE_DIR, f"{driver_id}.json")

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            print(f"Error loading profile: {e}")
            return None

    @classmethod
    def list_profiles(cls) -> list:
        """List all available profiles."""
        profiles = []
        if os.path.exists(config.PROFILE_DIR):
            for filename in os.listdir(config.PROFILE_DIR):
                if filename.endswith('.json'):
                    profiles.append(filename[:-5])  # Remove .json
        return profiles

    def __repr__(self) -> str:
        return (f"DriverProfile(id={self.driver_id}, "
                f"calibrated={self.is_calibrated}, "
                f"ear_mean={self.ear_mean:.3f}, "
                f"mar_mean={self.mar_mean:.3f})")

    def get_eye_thresholds(self) -> tuple:
        """Get (open_threshold, closed_threshold)."""
        return self.ear_mean, self.ear_closed_threshold

    def get_mouth_thresholds(self) -> tuple:
        """Get (normal_threshold, yawn_threshold)."""
        return self.mar_mean, self.mar_yawn_threshold

    def get_head_pose_range(self) -> tuple:
        """Get normal head pose range."""
        yaw_range = (self.yaw_center - self.yaw_std * 2,
                    self.yaw_center + self.yaw_std * 2)
        pitch_range = (self.pitch_center - self.pitch_std * 2,
                      self.pitch_center + self.pitch_std * 2)
        return yaw_range, pitch_range