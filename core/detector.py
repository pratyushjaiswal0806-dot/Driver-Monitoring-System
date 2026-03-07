"""Detector orchestrator that manages all detection modules."""

import numpy as np
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from detectors import (
    FaceAnalyzer, FaceData,
    EyeDetector, EyeState, EyeResult,
    MouthDetector, MouthState, MouthResult,
    HeadPoseEstimator, HeadPose,
    PhoneDetector
)
from scoring import RiskScorer, RiskScore
from calibration.driver_profile import DriverProfile
import config


@dataclass
class DetectionResults:
    """Complete detection results for a frame."""
    face_detected: bool
    face_data: Optional[FaceData]
    eye_result: Optional[EyeResult]
    mouth_result: Optional[MouthResult]
    head_pose: Optional[HeadPose]
    phone_detected: bool
    phone_detection: Optional[object]  # Detection object
    risk_score: Optional[RiskScore]

    def to_dict(self) -> Dict:
        """Convert to dictionary for display."""
        eye_state = self.eye_result.state.value if self.eye_result else EyeState.UNKNOWN.value
        attention = self.head_pose.direction.value if self.head_pose else 'unknown'
        return {
            'phone_detected': self.phone_detected,
            'eye_state': eye_state,
            'yawning': self.mouth_result.is_yawning if self.mouth_result else False,
            'attention': attention
        }


class DetectionOrchestrator:
    """Orchestrates all detector modules."""

    def __init__(self, use_yolo: bool = True):
        # Face detection (foundation for all other detections)
        self.face_analyzer = FaceAnalyzer()

        # Face-based detectors
        self.eye_detector = EyeDetector()
        self.mouth_detector = MouthDetector()
        self.head_pose_estimator = HeadPoseEstimator()

        # Phone detection
        self.use_yolo = use_yolo
        if use_yolo:
            self.phone_detector = PhoneDetector()
        else:
            self.phone_detector = None

        # Risk scoring
        self.risk_scorer = RiskScorer()

        # Driver profile
        self.driver_profile: Optional[DriverProfile] = None
        self.is_calibrated = False

        # Frame counter
        self.frame_count = 0
        self.face_detected_count = 0

    def set_profile(self, profile: DriverProfile):
        """Set the driver profile (after calibration or loading)."""
        self.driver_profile = profile
        self.is_calibrated = profile.is_calibrated

        print(f"Loaded profile: {profile.driver_id}")
        print(f"  EAR threshold: {profile.ear_closed_threshold:.3f}")
        print(f"  MAR threshold: {profile.mar_yawn_threshold:.3f}")

    def process_frame(self, frame: np.ndarray) -> DetectionResults:
        """
        Process a single frame through all detectors.

        Args:
            frame: BGR image from camera

        Returns:
            DetectionResults with all detections
        """
        self.frame_count += 1

        # 1. Face Detection (required for other detections)
        face_data = self.face_analyzer.process(frame)

        if face_data is None:
            return DetectionResults(
                face_detected=False,
                face_data=None,
                eye_result=None,
                mouth_result=None,
                head_pose=None,
                phone_detected=False,
                phone_detection=None,
                risk_score=self.risk_scorer.get_current_score()
            )

        self.face_detected_count += 1

        # Get face bounding box (normalized to pixel) for phone detection
        face_bbox = face_data.face_bbox

        # 2. Eye Detection
        eye_result = self.eye_detector.detect(
            face_data.landmarks, self.driver_profile
        )

        # 3. Mouth Detection
        mouth_result = self.mouth_detector.detect(
            face_data.landmarks, self.driver_profile
        )

        # 4. Head Pose Estimation
        head_pose = self.head_pose_estimator.estimate(
            face_data.landmarks, frame.shape, self.driver_profile
        )

        # 5. Phone Detection
        phone_detected = False
        phone_detection = None
        if self.phone_detector is not None:
            phone_detected, phone_detection = self.phone_detector.is_phone_detected(
                frame, face_bbox
            )

        # 6. Risk Scoring
        risk_score = self.risk_scorer.calculate(
            phone_detected=phone_detected,
            eye_state=eye_result,
            mouth_result=mouth_result,
            head_pose=head_pose,
            driver_profile=self.driver_profile
        )

        return DetectionResults(
            face_detected=True,
            face_data=face_data,
            eye_result=eye_result,
            mouth_result=mouth_result,
            head_pose=head_pose,
            phone_detected=phone_detected,
            phone_detection=phone_detection,
            risk_score=risk_score
        )

    def run_calibration(self, calibrator, frame: np.ndarray,
                        detections: DetectionResults) -> Tuple[bool, Optional[DriverProfile]]:
        """
        Run calibration step with current frame.

        Returns:
            Tuple of (is_complete, profile or None)
        """
        status, progress, time_remaining = calibrator.process_frame(
            frame,
            eye_result=detections.eye_result,
            mouth_result=detections.mouth_result,
            head_pose=detections.head_pose
        )

        if status.value == 'complete':
            profile = calibrator.generate_profile("default")
            if profile:
                self.set_profile(profile)
                profile.save()
                return True, profile
            return True, None

        return False, None

    def load_default_profile(self) -> bool:
        """Load the default profile if it exists."""
        profile = DriverProfile.load(config.DEFAULT_PROFILE_NAME)
        if profile:
            self.set_profile(profile)
            return True
        return False

    def reset_detectors(self):
        """Reset all detector states."""
        self.eye_detector.reset()
        self.mouth_detector.reset()
        self.head_pose_estimator.reset()
        if self.phone_detector:
            self.phone_detector.reset()
        self.risk_scorer.reset()

    def get_stats(self) -> Dict:
        """Get detection statistics."""
        face_ratio = (self.face_detected_count / max(1, self.frame_count))
        return {
            'frames_processed': self.frame_count,
            'face_detected_frames': self.face_detected_count,
            'face_detection_rate': face_ratio
        }

    def release(self):
        """Release all resources."""
        self.face_analyzer.release()
        if self.phone_detector:
            import gc
            gc.collect()
