"""Configuration constants for the Driver Monitoring System."""

import os

# =============================================================================
# CAMERA SETTINGS
# =============================================================================
CAMERA_INDEX = 0              # Default camera (0 = primary webcam)
FRAME_WIDTH = 640             # Frame width
FRAME_HEIGHT = 480            # Frame height
TARGET_FPS = 30               # Target frames per second

# =============================================================================
# CALIBRATION SETTINGS
# =============================================================================
CALIBRATION_DURATION_SEC = 30              # Duration of calibration phase
CALIBRATION_OPTIONAL = True                  # Allow skipping calibration
CALIBRATION_PROMPT = "Sit normally, look at camera. Calibrating..."
CALIBRATION_COUNTDOWN_MSG = "Starting calibration in {}..."

# Default thresholds (used when calibration is skipped)
DEFAULT_EAR_THRESHOLD = 0.25                 # Eyes open threshold
DEFAULT_EAR_CLOSED_THRESHOLD = 0.20          # Eyes closed threshold
DEFAULT_MAR_THRESHOLD = 0.35                 # Normal mouth at rest
DEFAULT_MAR_YAWN_THRESHOLD = 0.70            # Yawning threshold
DEFAULT_HEAD_YAW_THRESHOLD = 30              # degrees - looking left/right
DEFAULT_HEAD_PITCH_THRESHOLD = 25            # degrees - looking down

# Profile storage
PROFILE_DIR = os.path.join(os.path.dirname(__file__), 'profiles')
DEFAULT_PROFILE_NAME = 'default'

# =============================================================================
# DETECTION SETTINGS
# =============================================================================
# MediaPipe Face Mesh
MP_MAX_FACES = 1                             # Track only 1 face
MP_DETECTION_CONFIDENCE = 0.5
MP_TRACKING_CONFIDENCE = 0.5

# YOLOv8
YOLO_MODEL = 'yolov8s.pt'                    # User selected: better accuracy
YOLO_CONFIDENCE = 0.5                        # Minimum detection confidence
YOLO_PHONE_CLASS_NAMES = ['cell phone', 'phone', 'mobile phone']

# Face landmark indices (MediaPipe Face Mesh 468 landmarks)
# Eyes (6 points each)
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

# Mouth (for MAR calculation)
MOUTH_TOP = 13        # Upper lip center
MOUTH_BOTTOM = 14     # Lower lip center
MOUTH_LEFT = 78       # Left mouth corner
MOUTH_RIGHT = 308     # Right mouth corner

# Head pose (PnP model points)
FACE_MODEL_POINTS = [
    1,      # Nose tip
    152,    # Chin
    263,    # Left eye outer corner
    33,     # Right eye outer corner
    287,    # Left mouth corner
    57      # Right mouth corner
]

# =============================================================================
# TEMPORAL SMOOTHING
# =============================================================================
SMOOTHING_ALPHA = 0.3                              # EWMA smoothing factor
ALERT_TRIGGER_FRAMES = 30                          # ~1 second at 30fps
BLINK_MIN_FRAMES = 3                               # Minimum blink duration
BLINK_MAX_FRAMES = 12                              # Maximum normal blink
EYES_CLOSED_ALERT_FRAMES = 60                      # ~2 seconds
MOUTH_OPEN_ALERT_FRAMES = 30                       # ~1 second
HEAD_AWAY_ALERT_FRAMES = 45                        # ~1.5 seconds

# =============================================================================
# RISK SCORING
# =============================================================================
# Increased weights so single issues can trigger higher risk alerts
RISK_WEIGHTS = {
    'phone': 55,      # Phone: up to 55% risk alone
    'drowsy': 55,     # Drowsy: up to 55% risk alone
    'yawning': 35,    # Yawning: up to 35% risk alone
    'looking_away': 35  # Looking away: up to 35% risk alone
}
# Total: 180 max (capped at 100)

# Risk thresholds for UI display (0-20 Safe, 20-40 Mild, 40-60 Warning, 60-80 High, 80-100 Critical)
RISK_THRESHOLDS = {
    'safe': (0, 20),
    'mild': (20, 40),
    'warning': (40, 60),
    'high': (60, 80),
    'danger': (80, 100)
}

# =============================================================================
# AUDIO SETTINGS
# =============================================================================
AUDIO_ENABLED = True
AUDIO_GRADUATED = True
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 1
AUDIO_BUFFER = 2048

AUDIO_FREQ_MIN = 440          # Hz (A4)
AUDIO_FREQ_MAX = 880          # Hz (A5)
AUDIO_DURATION_MS = 200
AUDIO_VOLUME = 0.9  # Loud enough to wake someone

# =============================================================================
# DRIVER ALERT BEEP SYSTEM
# =============================================================================
# Risk Score Levels:
#   0-20: Safe      - No sound, display only
#   20-40: Mild     - Beep every 6s, 800Hz, 200ms
#   40-60: Warning  - "beep beep" every 3s, 1200Hz, 250ms
#   60-80: High     - "beep beep beep" every 2s, 1800Hz, 300ms
#   80-100: Critical - Continuous "beep beep beep beep", 2500Hz, 400ms

BEEP_CONFIG = {
    'mild': {
        'interval': 6.0,
        'frequency': 800,
        'duration_ms': 200,
        'count': 1,
    },
    'warning': {
        'interval': 3.0,
        'frequency': 1200,
        'duration_ms': 250,
        'count': 2,
    },
    'high_risk': {
        'interval': 2.0,
        'frequency': 1800,
        'duration_ms': 300,
        'count': 3,
    },
    'critical': {
        'interval': 0.0,  # Continuous (no pause between beep groups)
        'frequency': 2500,
        'duration_ms': 400,
        'count': 4,
    },
}

# Screen flash settings for critical alert
CRITICAL_FLASH_ENABLED = True
CRITICAL_FLASH_INTERVAL = 0.5  # Flash every 0.5 seconds

# Beep intervals by risk level (seconds between beeps)
AUDIO_INTERVALS = {
    'safe': float('inf'),     # No beeps
    'warning': 2.0,           # Every 2 seconds
    'danger': 1.0,            # Every 1 second
    'critical': 0.3           # Every 0.3 seconds
}

# =============================================================================
# DISPLAY SETTINGS
# =============================================================================
# Colors (BGR format for OpenCV)
COLOR_SAFE = (0, 255, 0)           # Green
COLOR_WARNING = (0, 165, 255)       # Orange
COLOR_DANGER = (0, 0, 255)          # Red
COLOR_NEUTRAL = (255, 255, 255)     # White
COLOR_INFO = (255, 255, 0)          # Cyan

# UI Layout
PANEL_WIDTH = 250
PANEL_PADDING = 10
FONT_SCALE_SMALL = 0.5
FONT_SCALE_NORMAL = 0.7
FONT_SCALE_LARGE = 1.0
FONT_THICKNESS = 2

# Recovery timeline
TIMELINE_SECONDS = 10
TIMELINE_HEIGHT = 80

# =============================================================================
# STATUS MESSAGES
# =============================================================================
STATUS_MESSAGES = {
    'phone': {
        True: 'PHONE DETECTED',
        False: 'No Phone'
    },
    'eyes': {
        'open': 'Eyes Open',
        'closed': 'EYES CLOSED',
        'drowsy': 'DROWSY!'
    },
    'yawning': {
        True: 'YAWNING',
        False: 'No Yawn'
    },
    'attention': {
        'front': 'Looking Front',
        'away': 'LOOKING AWAY',
        'left': 'LEFT',
        'right': 'RIGHT',
        'down': 'LOOKING DOWN'
    },
    'risk': {
        'safe': 'SAFE',
        'warning': 'WARNING',
        'danger': 'DANGER'
    }
}

# Key bindings
KEY_QUIT = ord('q')
KEY_CALIBRATE = ord('c')
KEY_RESET = ord('r')
KEY_PAUSE = ord('p')
KEY_TEST_BEEP = ord('b')
