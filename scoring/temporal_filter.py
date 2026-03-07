"""Temporal filtering for smooth detection."""

import numpy as np
from collections import deque
from typing import List, Optional
import config


class TemporalFilter:
    """Exponential weighted moving average filter."""

    def __init__(self, alpha: float = config.SMOOTHING_ALPHA):
        self.alpha = alpha
        self.value: Optional[float] = None
        self.initialized = False

    def update(self, new_value: float) -> float:
        """Update with new value and return smoothed result."""
        if not self.initialized:
            self.value = new_value
            self.initialized = True
        else:
            self.value = self.alpha * new_value + (1 - self.alpha) * self.value
        return self.value

    def reset(self):
        """Reset filter."""
        self.value = None
        self.initialized = False

    def get_value(self) -> Optional[float]:
        """Get current smoothed value."""
        return self.value


class SmoothingBuffer:
    """Fixed-size buffer for smoothing."""

    def __init__(self, size: int = 10):
        self.size = size
        self.buffer: deque = deque(maxlen=size)

    def append(self, value: float):
        """Add value to buffer."""
        self.buffer.append(value)

    def get_mean(self) -> float:
        """Get mean of buffer."""
        if len(self.buffer) == 0:
            return 0.0
        return float(np.mean(self.buffer))

    def get_median(self) -> float:
        """Get median of buffer."""
        if len(self.buffer) == 0:
            return 0.0
        return float(np.median(self.buffer))

    def get_std(self) -> float:
        """Get standard deviation."""
        if len(self.buffer) < 2:
            return 0.0
        return float(np.std(self.buffer))

    def is_full(self) -> bool:
        """Check if buffer is full."""
        return len(self.buffer) == self.size

    def clear(self):
        """Clear buffer."""
        self.buffer.clear()

    def __len__(self) -> int:
        return len(self.buffer)
