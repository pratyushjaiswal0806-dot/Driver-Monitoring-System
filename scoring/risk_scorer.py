"""Risk scoring system for driver monitoring."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from collections import deque

import config


class RiskLevel(Enum):
    """Risk level classifications."""
    SAFE = "safe"
    MILD = "mild"
    WARNING = "warning"
    HIGH = "high"
    DANGER = "danger"


@dataclass
class RiskScore:
    """Complete risk score with component breakdown."""
    total: float = 0.0
    level: RiskLevel = RiskLevel.SAFE
    phone_score: float = 0.0
    drowsy_score: float = 0.0
    yawning_score: float = 0.0
    attention_score: float = 0.0
    signals: Dict[str, bool] = field(default_factory=dict)
    history: List[float] = field(default_factory=list)

    def get_color(self) -> tuple:
        """Get color for current risk level."""
        if self.level == RiskLevel.SAFE:
            return config.COLOR_SAFE
        elif self.level == RiskLevel.MILD:
            return (100, 255, 100)  # Light green
        elif self.level == RiskLevel.WARNING:
            return config.COLOR_WARNING
        elif self.level == RiskLevel.HIGH:
            return (0, 0, 255)  # Red
        else:  # DANGER
            return config.COLOR_DANGER

    def get_status_text(self) -> str:
        """Get status text."""
        return self.level.value.upper()


class RiskScorer:
    """Calculate driver risk score from all detection signals."""

    def __init__(self,
                 weights: Dict[str, int] = None,
                 max_history: int = 300):
        """
        Initialize risk scorer.

        Args:
            weights: Dictionary of risk component weights
            max_history: Maximum history samples (10 sec at 30fps)
        """
        self.weights = weights or config.RISK_WEIGHTS
        self.max_history = max_history

        # History for timeline
        self.history: deque = deque(maxlen=max_history)

        # Current and previous scores
        self.current_score = RiskScore()
        self.previous_raw_score = 0.0

        # Temporal smoothing
        self.smoothed_score = 0.0
        self.alpha = config.SMOOTHING_ALPHA

        # Component scores for debugging
        self.components = {
            'phone': 0.0,
            'drowsy': 0.0,
            'yawning': 0.0,
            'attention': 0.0
        }

    def calculate(self,
                  phone_detected: bool,
                  eye_state,
                  mouth_result,
                  head_pose,
                  driver_profile=None) -> RiskScore:
        """
        Calculate risk score from all detector outputs.

        Args:
            phone_detected: Whether phone is detected
            eye_state: EyeState from EyeDetector
            mouth_result: MouthResult from MouthDetector
            head_pose: HeadPose from HeadPoseEstimator
            driver_profile: Optional DriverProfile for personalized thresholds

        Returns:
            RiskScore with component breakdown
        """
        # Calculate component scores
        phone_score = self._calculate_phone_score(phone_detected)
        drowsy_score = self._calculate_drowsy_score(eye_state, driver_profile)
        yawning_score = self._calculate_yawning_score(mouth_result)
        attention_score = self._calculate_attention_score(head_pose, driver_profile)

        # Store component scores
        self.components['phone'] = phone_score
        self.components['drowsy'] = drowsy_score
        self.components['yawning'] = yawning_score
        self.components['attention'] = attention_score

        # Calculate total (weighted sum)
        raw_score = (phone_score * self.weights['phone'] +
                    drowsy_score * self.weights['drowsy'] +
                    yawning_score * self.weights['yawning'] +
                    attention_score * self.weights['looking_away'])

        # Apply temporal smoothing
        if self.previous_raw_score == 0:
            self.smoothed_score = raw_score
        else:
            self.smoothed_score = (self.alpha * raw_score +
                                 (1 - self.alpha) * self.smoothed_score)

        self.previous_raw_score = raw_score
        total_score = min(self.smoothed_score, 100.0)

        # Determine risk level
        level = self._get_risk_level(total_score)

        # Create signals dict
        signals = {
            'phone_detected': phone_detected,
            'eyes_closed': eye_state.state.value == 'closed' if eye_state else False,
            'drowsy': eye_state.state.value == 'drowsy' if eye_state else False,
            'yawning': mouth_result.is_yawning if mouth_result else False,
            'looking_away': head_pose.looking_away if head_pose else False
        }

        # Update history
        self.history.append(total_score)

        # Create score
        score = RiskScore(
            total=total_score,
            level=level,
            phone_score=phone_score * self.weights['phone'],
            drowsy_score=drowsy_score * self.weights['drowsy'],
            yawning_score=yawning_score * self.weights['yawning'],
            attention_score=attention_score * self.weights['looking_away'],
            signals=signals,
            history=list(self.history)
        )

        self.current_score = score
        return score

    def _calculate_phone_score(self, phone_detected: bool) -> float:
        """Calculate phone distraction score (0-1)."""
        return 1.0 if phone_detected else 0.0

    def _calculate_drowsy_score(self, eye_state, driver_profile=None) -> float:
        """Calculate drowsiness score (0-1)."""
        if eye_state is None:
            return 0.0

        if eye_state.state.value == 'drowsy':
            return 1.0  # Full drowsiness
        elif eye_state.state.value == 'closed':
            # Partial score based on duration
            duration = eye_state.eyes_closed_duration
            return min(duration / 2.0, 0.8)  # Max 0.8 if not yet drowsy

        return 0.0

    def _calculate_yawning_score(self, mouth_result) -> float:
        """Calculate yawning score (0-1)."""
        if mouth_result is None:
            return 0.0

        if mouth_result.is_yawning:
            return 1.0
        elif mouth_result.state.value == 'yawning':
            return 0.8

        return 0.0

    def _calculate_attention_score(self, head_pose, driver_profile=None) -> float:
        """Calculate attention/distraction score (0-1)."""
        if head_pose is None:
            return 0.0

        if head_pose.looking_away:
            # Score based on duration
            duration = head_pose.away_duration
            return min(duration / 3.0, 1.0)

        return 0.0

    def _get_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level from score."""
        if score < config.RISK_THRESHOLDS['mild'][0]:
            return RiskLevel.SAFE
        elif score < config.RISK_THRESHOLDS['warning'][0]:
            return RiskLevel.MILD
        elif score < config.RISK_THRESHOLDS['high'][0]:
            return RiskLevel.WARNING
        elif score < config.RISK_THRESHOLDS['danger'][0]:
            return RiskLevel.HIGH
        else:
            return RiskLevel.DANGER

    def reset(self):
        """Reset scorer state."""
        self.history.clear()
        self.smoothed_score = 0.0
        self.previous_raw_score = 0.0
        self.current_score = RiskScore()
        self.components = {k: 0.0 for k in self.components}

    def get_current_score(self) -> RiskScore:
        """Get current score."""
        return self.current_score

    def get_history(self) -> List[float]:
        """Get score history."""
        return list(self.history)

    def get_peak_risk(self, window: int = 30) -> float:
        """Get peak risk in last N frames."""
        recent = list(self.history)[-window:] if len(self.history) >= window else list(self.history)
        return max(recent) if recent else 0.0

    def get_average_risk(self, window: int = 30) -> float:
        """Get average risk in last N frames."""
        if len(self.history) < window:
            return sum(self.history) / max(len(self.history), 1)
        recent = list(self.history)[-window:]
        return sum(recent) / window

    def get_component_scores(self) -> Dict[str, float]:
        """Get current component scores."""
        return self.components.copy()