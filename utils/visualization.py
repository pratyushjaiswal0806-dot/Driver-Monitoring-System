"""Visualization utilities for drawing on frames."""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import config


def draw_face_landmarks(frame: np.ndarray,
                        landmarks: np.ndarray,
                        color: Tuple[int, int, int] = config.COLOR_NEUTRAL) -> np.ndarray:
    """Draw face mesh landmarks on frame."""
    h, w = frame.shape[:2]

    for landmark in landmarks:
        x = int(landmark[0] * w)
        y = int(landmark[1] * h)
        cv2.circle(frame, (x, y), 1, color, -1)

    return frame


def draw_eye_region(frame: np.ndarray,
                    landmarks: np.ndarray,
                    eye_indices: List[int],
                    color: Tuple[int, int, int] = config.COLOR_INFO) -> np.ndarray:
    """Draw eye region with connecting lines."""
    h, w = frame.shape[:2]

    points = []
    for idx in eye_indices:
        x = int(landmarks[idx][0] * w)
        y = int(landmarks[idx][1] * h)
        points.append((x, y))
        cv2.circle(frame, (x, y), 2, color, -1)

    # Draw connections (eye outline)
    connections = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)]
    for i, j in connections:
        cv2.line(frame, points[i], points[j], color, 1)

    return frame


def draw_detection_box(frame: np.ndarray,
                       bbox: Tuple[int, int, int, int],
                       label: str,
                       confidence: float,
                       color: Tuple[int, int, int] = config.COLOR_INFO) -> np.ndarray:
    """Draw bounding box with label."""
    x1, y1, x2, y2 = bbox

    # Draw box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    # Draw label background
    label_text = f"{label}: {confidence:.2f}"
    (text_w, text_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX,
                                          config.FONT_SCALE_NORMAL, 1)
    cv2.rectangle(frame, (x1, y1 - text_h - 10),
                  (x1 + text_w + 10, y1), color, -1)

    # Draw label text
    cv2.putText(frame, label_text, (x1 + 5, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE_NORMAL,
                config.COLOR_NEUTRAL, 1)

    return frame


def draw_risk_bar(frame: np.ndarray,
                  risk_score: float,
                  x: int = 10,
                  y: int = 10,
                  width: int = 200,
                  height: int = 30) -> np.ndarray:
    """Draw risk score bar with color coding."""
    # Determine color based on risk level
    if risk_score < 30:
        color = config.COLOR_SAFE
        status = "SAFE"
    elif risk_score < 60:
        color = config.COLOR_WARNING
        status = "WARNING"
    else:
        color = config.COLOR_DANGER
        status = "DANGER"

    # Background
    cv2.rectangle(frame, (x, y), (x + width, y + height), (50, 50, 50), -1)
    cv2.rectangle(frame, (x, y), (x + width, y + height),
                  config.COLOR_NEUTRAL, 1)

    # Filled portion
    filled_width = int(width * (risk_score / 100.0))
    cv2.rectangle(frame, (x, y), (x + filled_width, y + height), color, -1)

    # Text
    text = f"Risk: {risk_score:.0f}% [{status}]"
    cv2.putText(frame, text, (x + 5, y + height - 5),
                cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE_NORMAL,
                config.COLOR_NEUTRAL, 2)

    return frame


def draw_status_panel(frame: np.ndarray,
                      detections: Dict[str, any],
                      x: int = None,
                      y: int = 60) -> np.ndarray:
    """Draw status panel with all detection states."""
    h, w = frame.shape[:2]

    if x is None:
        x = w - config.PANEL_WIDTH - 10

    panel_height = 180

    # Panel background
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + config.PANEL_WIDTH,
                  y + panel_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Draw border
    cv2.rectangle(frame, (x, y), (x + config.PANEL_WIDTH,
                  y + panel_height), config.COLOR_NEUTRAL, 1)

    # Title
    cv2.putText(frame, "STATUS", (x + 10, y + 25),
                cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE_LARGE,
                config.COLOR_NEUTRAL, 2)
    cv2.line(frame, (x, y + 35), (x + config.PANEL_WIDTH, y + 35),
             config.COLOR_NEUTRAL, 1)

    line_y = y + 55
    line_height = 28

    # Phone status
    phone = detections.get('phone_detected', False)
    phone_color = config.COLOR_DANGER if phone else config.COLOR_SAFE
    phone_text = "Phone: " + ("DETECTED" if phone else "No")
    cv2.putText(frame, phone_text, (x + 10, line_y),
                cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE_NORMAL,
                phone_color, 2)

    # Eyes status
    line_y += line_height
    eyes = detections.get('eye_state', 'open')
    eyes = getattr(eyes, 'value', eyes)
    eyes = str(eyes).lower()
    if eyes == 'drowsy':
        eyes_color = config.COLOR_DANGER
    elif eyes == 'closed':
        eyes_color = config.COLOR_WARNING
    else:
        eyes_color = config.COLOR_SAFE
    eyes_text = f"Eyes: {eyes.upper()}"
    cv2.putText(frame, eyes_text, (x + 10, line_y),
                cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE_NORMAL,
                eyes_color, 2)

    # Yawning status
    line_y += line_height
    yawning = detections.get('yawning', False)
    yawn_color = config.COLOR_WARNING if yawning else config.COLOR_SAFE
    yawn_text = "Yawn: " + ("YES" if yawning else "No")
    cv2.putText(frame, yawn_text, (x + 10, line_y),
                cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE_NORMAL,
                yawn_color, 2)

    # Attention status
    line_y += line_height
    attention = detections.get('attention', 'front')
    attention = getattr(attention, 'value', attention)
    attention = str(attention).lower()
    if attention == 'front':
        attn_color = config.COLOR_SAFE
        attn_text = "Attention: FRONT"
    else:
        attn_color = config.COLOR_WARNING
        attn_text = f"Attention: {attention.upper()}"
    cv2.putText(frame, attn_text, (x + 10, line_y),
                cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE_NORMAL,
                attn_color, 2)

    return frame


def draw_timeline(frame: np.ndarray,
                  risk_history: List[float],
                  x: int = 10,
                  y: int = None,
                  width: int = 400,
                  height: int = 60) -> np.ndarray:
    """Draw risk score timeline graph."""
    h, w = frame.shape[:2]

    if y is None:
        y = h - height - 10

    if len(risk_history) < 2:
        return frame

    # Panel background
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + width, y + height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Draw title
    cv2.putText(frame, "Risk History (10s)", (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE_SMALL,
                config.COLOR_NEUTRAL, 1)

    # Draw grid lines
    cv2.line(frame, (x, y), (x + width, y), config.COLOR_NEUTRAL, 1)
    cv2.line(frame, (x, y + height), (x + width,
             y + height), config.COLOR_NEUTRAL, 1)

    # Safe/Warning/Danger zones
    safe_y = y + height - int(height * 0.3)  # 30%
    danger_y = y + height - int(height * 0.6)  # 60%
    cv2.line(frame, (x, safe_y), (x + width, safe_y), config.COLOR_SAFE, 1)
    cv2.line(frame, (x, danger_y), (x + width,
             danger_y), config.COLOR_DANGER, 1)

    # Draw history line
    points = []
    num_points = min(len(risk_history), 100)

    for i, risk in enumerate(risk_history[-num_points:]):
        px = x + int((i / (num_points - 1)) * width)
        py = y + height - int((risk / 100.0) * height)
        points.append((px, py))

    if len(points) > 1:
        for i in range(len(points) - 1):
            # Color based on risk level
            risk = risk_history[-(num_points - i)]
            if risk < 30:
                color = config.COLOR_SAFE
            elif risk < 60:
                color = config.COLOR_WARNING
            else:
                color = config.COLOR_DANGER
            cv2.line(frame, points[i], points[i + 1], color, 2)

    return frame


def create_status_overlay(frame: np.ndarray,
                          risk_score: float,
                          detections: Dict[str, any],
                          show_landmarks: bool = False,
                          landmarks: Optional[np.ndarray] = None) -> np.ndarray:
    """Create full status overlay on frame."""
    overlay = frame.copy()

    # Draw risk bar at top
    overlay = draw_risk_bar(overlay, risk_score, x=10, y=10)

    # Draw status panel
    overlay = draw_status_panel(overlay, detections)

    # Draw landmarks if requested
    if show_landmarks and landmarks is not None:
        overlay = draw_face_landmarks(overlay, landmarks)

    return overlay


def draw_calibration_progress(frame: np.ndarray,
                              progress: float,
                              time_remaining: int) -> np.ndarray:
    """Draw calibration progress overlay."""
    h, w = frame.shape[:2]

    # Semi-transparent overlay
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    # Center text
    center_x = w // 2
    center_y = h // 2

    # Title
    cv2.putText(frame, "CALIBRATION", (center_x - 150, center_y - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, config.COLOR_INFO, 3)

    # Instruction
    cv2.putText(frame, "Sit normally, look at camera", (center_x - 200, center_y),
                cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE_NORMAL,
                config.COLOR_NEUTRAL, 2)

    # Progress bar
    bar_width = 300
    bar_height = 30
    bar_x = center_x - bar_width // 2
    bar_y = center_y + 50

    # Background
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                  (50, 50, 50), -1)
    # Progress
    filled = int(bar_width * progress)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + filled, bar_y + bar_height),
                  config.COLOR_INFO, -1)
    # Border
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                  config.COLOR_NEUTRAL, 2)

    # Time remaining
    time_text = f"{time_remaining}s remaining"
    cv2.putText(frame, time_text, (center_x - 100, bar_y + bar_height + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, config.COLOR_INFO, 2)

    return frame


def draw_alert_overlay(frame: np.ndarray, message: str) -> np.ndarray:
    """Draw urgent alert overlay on frame."""
    h, w = frame.shape[:2]

    # Flash red tint
    overlay = frame.copy()
    red_tint = np.full_like(frame, (0, 0, 100), dtype=np.uint8)
    cv2.addWeighted(overlay, 0.7, red_tint, 0.3, 0, frame)

    # Center alert text
    center_x = w // 2
    center_y = h // 2

    # Large warning text
    (text_w, text_h), _ = cv2.getTextSize(
        message, cv2.FONT_HERSHEY_SIMPLEX, 2.0, 4)
    text_x = center_x - text_w // 2
    text_y = center_y

    # Draw text with outline
    cv2.putText(frame, message, (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 6)
    cv2.putText(frame, message, (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX, 2.0, config.COLOR_DANGER, 3)

    return frame
