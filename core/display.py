"""Display manager for UI rendering."""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple

import config
from utils.visualization import (
    draw_risk_bar,
    draw_status_panel,
    draw_timeline,
    draw_calibration_progress,
    draw_alert_overlay
)
from scoring.risk_scorer import RiskScore


class DisplayManager:
    """Manages the display and UI rendering."""

    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self.window_name = "Driver Monitor System"

        # UI state
        self.show_landmarks = False
        self.show_raw_feed = False
        self.alert_message = None
        self.alert_start_time = 0

        # Create window
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

    def render(self, frame: np.ndarray,
               risk_score: RiskScore,
               detections: Dict,
               landmarks: Optional[np.ndarray] = None,
               show_overlay: bool = True) -> np.ndarray:
        """
        Render the main display with all overlays.

        Args:
            frame: Original camera frame
            risk_score: Current risk score
            detections: Detection results dictionary
            landmarks: Optional face landmarks
            show_overlay: Whether to show UI overlay

        Returns:
            Rendered frame
        """
        display = frame.copy()

        if show_overlay:
            # Draw risk bar at top
            display = draw_risk_bar(display, risk_score.total, x=10, y=10)

            # Draw status panel
            display = draw_status_panel(display, detections)

            # Draw landmarks if enabled
            if self.show_landmarks and landmarks is not None:
                from utils.visualization import draw_face_landmarks
                display = draw_face_landmarks(display, landmarks)

            # Draw timeline
            display = draw_timeline(display, risk_score.history)

        return display

    def render_calibration(self, frame: np.ndarray,
                          progress: float,
                          time_remaining: int) -> np.ndarray:
        """Render calibration screen."""
        return draw_calibration_progress(frame, progress, time_remaining)

    def show_alert(self, message: str, duration_ms: int = 2000):
        """Show temporary alert."""
        self.alert_message = message
        self.alert_start_time = cv2.getTickCount()

    def render_alert_if_active(self, frame: np.ndarray) -> np.ndarray:
        """Render active alert if within duration."""
        if self.alert_message is None:
            return frame

        # Check if alert has expired
        elapsed = (cv2.getTickCount() - self.alert_start_time) / cv2.getTickFrequency() * 1000
        if elapsed > 2000:  # 2 seconds
            self.alert_message = None
            return frame

        return draw_alert_overlay(frame, self.alert_message)

    def get_status_color(self, risk_level: str) -> Tuple[int, int, int]:
        """Get color for risk level."""
        if risk_level == "safe":
            return config.COLOR_SAFE
        elif risk_level == "warning":
            return config.COLOR_WARNING
        else:
            return config.COLOR_DANGER

    def create_menu_frame(self) -> np.ndarray:
        """Create startup menu frame."""
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        center_x = self.width // 2
        center_y = self.height // 2

        # Title
        cv2.putText(frame, "Driver Monitor System",
                   (center_x - 200, center_y - 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, config.COLOR_INFO, 3)

        # Menu options
        options = [
            "[1] Quick Start (use default settings)",
            "[2] Calibrate (30 sec, more accurate)",
            "",
            "Press 1 or 2 to begin..."
        ]

        y_offset = center_y - 50
        for option in options:
            cv2.putText(frame, option,
                       (center_x - 200, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                       config.COLOR_NEUTRAL, 2)
            y_offset += 50

        # Instructions
        cv2.putText(frame, "[Q] Quit  [C] Calibrate",
                   (center_x - 150, self.height - 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, config.COLOR_INFO, 1)

        return frame

    def create_waiting_frame(self) -> np.ndarray:
        """Create waiting for face frame."""
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        center_x = self.width // 2
        center_y = self.height // 2

        cv2.putText(frame, "Waiting for face...",
                   (center_x - 150, center_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, config.COLOR_WARNING, 2)

        cv2.putText(frame, "Position yourself in camera view",
                   (center_x - 175, center_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, config.COLOR_NEUTRAL, 2)

        return frame

    def show(self, frame: np.ndarray):
        """Show frame in window."""
        cv2.imshow(self.window_name, frame)

    def should_quit(self) -> bool:
        """Check if user wants to quit."""
        key = cv2.waitKey(1) & 0xFF
        return key == config.KEY_QUIT

    def get_key(self) -> int:
        """Get key press."""
        return cv2.waitKey(1) & 0xFF

    def release(self):
        """Release window."""
        cv2.destroyAllWindows()
