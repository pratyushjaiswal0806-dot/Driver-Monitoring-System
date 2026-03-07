"""Camera capture module using OpenCV."""

import cv2
import numpy as np
from typing import Optional, Tuple
import config


class Camera:
    """Webcam capture wrapper with frame preprocessing."""

    def __init__(self, camera_index: int = config.CAMERA_INDEX):
        self.camera_index = camera_index
        self.cap: Optional[cv2.VideoCapture] = None
        self.width = config.FRAME_WIDTH
        self.height = config.FRAME_HEIGHT
        self.fps = config.TARGET_FPS
        self.frame_count = 0

    def start(self) -> bool:
        """
        Initialize and start the camera.

        Returns:
            True if camera opened successfully
        """
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            # Try with default backend
            self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            print(f"Error: Could not open camera {self.camera_index}")
            return False

        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        # Read actual properties
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or config.TARGET_FPS

        print(f"Camera started: {self.width}x{self.height} @ {self.fps}fps")
        return True

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read a frame from the camera.

        Returns:
            Tuple of (success, frame)
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None

        ret, frame = self.cap.read()

        if ret:
            self.frame_count += 1
            # Ensure frame is in correct format
            if len(frame.shape) == 2:
                # Convert grayscale to BGR
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        return ret, frame

    def release(self):
        """Release the camera."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            print("Camera released")

    def get_frame_count(self) -> int:
        """Get total frames read."""
        return self.frame_count

    def get_fps(self) -> float:
        """Get actual camera FPS."""
        return self.fps

    def get_resolution(self) -> Tuple[int, int]:
        """Get camera resolution (width, height)."""
        return self.width, self.height

    def is_ready(self) -> bool:
        """Check if camera is ready."""
        return self.cap is not None and self.cap.isOpened()

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


class FrameBuffer:
    """Buffer for frame processing with preprocessing options."""

    def __init__(self, target_size: Tuple[int, int] = (640, 480)):
        self.target_size = target_size
        self.original_frame: Optional[np.ndarray] = None
        self.processed_frame: Optional[np.ndarray] = None

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for detection.

        Args:
            frame: Input BGR frame

        Returns:
            Processed frame
        """
        self.original_frame = frame.copy()

        # Resize if needed
        h, w = frame.shape[:2]
        if (w, h) != self.target_size:
            frame = cv2.resize(frame, self.target_size)

        self.processed_frame = frame
        return frame

    def get_original(self) -> Optional[np.ndarray]:
        """Get original unprocessed frame."""
        return self.original_frame

    def get_processed(self) -> Optional[np.ndarray]:
        """Get processed frame."""
        return self.processed_frame


def test_camera():
    """Test camera functionality."""
    print("Testing camera...")

    cam = Camera()
    if not cam.start():
        print("Failed to open camera")
        return

    print(f"Camera resolution: {cam.get_resolution()}")

    # Test read
    ret, frame = cam.read()
    if ret:
        print(f"Frame shape: {frame.shape}")
        print(f"Frame dtype: {frame.dtype}")
        print("Camera test PASSED")
    else:
        print("Camera test FAILED - could not read frame")

    cam.release()


if __name__ == '__main__':
    test_camera()