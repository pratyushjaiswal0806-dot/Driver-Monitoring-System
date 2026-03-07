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
RISK_WEIGHTS = {
    'phone': 40,
    'drowsy': 40,
    'yawning': 20,
    'looking_away': 20
}

RISK_THRESHOLDS = {
    'safe': (0, 30),
    'warning': (30, 60),
    'danger': (60, 100)
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
AUDIO_VOLUME = 0.5

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
