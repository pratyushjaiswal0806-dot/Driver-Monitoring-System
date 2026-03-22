import unittest

import numpy as np

from utils.math_utils import calculate_iod, calculate_normalized_ear


def build_landmarks(scale: float) -> np.ndarray:
    """Build synthetic MediaPipe landmarks at a given scale."""
    landmarks = np.zeros((468, 3), dtype=float)

    # Left eye outer corner and right eye outer corner.
    landmarks[33] = np.array([0.0, 0.0, 0.0])
    landmarks[263] = np.array([24.0 * scale, 0.0, 0.0])

    # Left eye geometry.
    landmarks[160] = np.array([0.0, 2.0 * scale, 0.0])
    landmarks[158] = np.array([1.0 * scale, 3.0 * scale, 0.0])
    landmarks[133] = np.array([4.0 * scale, 0.0, 0.0])
    landmarks[153] = np.array([1.0 * scale, -1.0 * scale, 0.0])
    landmarks[144] = np.array([0.0, -2.0 * scale, 0.0])

    # Right eye geometry.
    landmarks[362] = np.array([20.0 * scale, 0.0, 0.0])
    landmarks[385] = np.array([20.0 * scale, 2.0 * scale, 0.0])
    landmarks[387] = np.array([21.0 * scale, 3.0 * scale, 0.0])
    landmarks[373] = np.array([21.0 * scale, -1.0 * scale, 0.0])
    landmarks[380] = np.array([20.0 * scale, -2.0 * scale, 0.0])

    return landmarks


class TestMathUtils(unittest.TestCase):
    def test_calculate_iod_fallback_when_coincident(self):
        landmarks = np.zeros((468, 3), dtype=float)
        landmarks[33] = np.array([1.0, 1.0, 0.0])
        landmarks[263] = np.array([1.0, 1.0, 0.0])

        self.assertEqual(calculate_iod(landmarks), 1.0)

    def test_calculate_normalized_ear_is_scale_stable(self):
        near_landmarks = build_landmarks(0.5)
        far_landmarks = build_landmarks(2.0)

        near_ear = calculate_normalized_ear(near_landmarks)
        far_ear = calculate_normalized_ear(far_landmarks)

        self.assertAlmostEqual(near_ear, far_ear, places=6)


if __name__ == '__main__':
    unittest.main()
