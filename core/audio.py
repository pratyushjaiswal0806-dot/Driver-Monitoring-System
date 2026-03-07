"""Audio manager for graduated alerts."""

try:
 import pygame.mixer
 import pygame.sndarray
 PYGAME_AVAILABLE = True
except ImportError:
 PYGAME_AVAILABLE = False

import numpy as np
import time
from typing import Optional

import config


class AudioManager:
    """Graduated audio feedback manager."""

    # Debug flag - set to True to see audio debug messages
    DEBUG = True

    def __init__(self, enabled: bool = config.AUDIO_ENABLED):
        self.enabled = enabled and PYGAME_AVAILABLE and config.AUDIO_ENABLED
        self.last_beep_time = 0
        self.current_risk = 0
        self.is_initialized = False

        # Debug: Report audio status
        if not PYGAME_AVAILABLE:
            if self.DEBUG:
                print("[AUDIO] Disabled: pygame not available")
        elif not config.AUDIO_ENABLED:
            if self.DEBUG:
                print("[AUDIO] Disabled: AUDIO_ENABLED = False in config")
        elif not enabled:
            if self.DEBUG:
                print("[AUDIO] Disabled: disabled by parameter")
        else:
            if self.DEBUG:
                print("[AUDIO] Initializing...")

        if self.enabled:
            try:
                pygame.mixer.init(
                    frequency=config.AUDIO_SAMPLE_RATE,
                    size=-16,
                    channels=config.AUDIO_CHANNELS,
                    buffer=config.AUDIO_BUFFER
                )
                self.is_initialized = True
                if self.DEBUG:
                    print("[AUDIO] Initialized successfully - playing test sound")
                # Play test sound to verify audio works
                self.play_test_beep()
            except Exception as e:
                print(f"[AUDIO] ERROR: Initialization failed: {e}")
                self.enabled = False

    def generate_tone(self, frequency: float, duration_ms: int, volume: float = 0.5) -> np.ndarray:
        """Generate a tone as numpy array (2D for stereo compatibility)."""
        sample_count = int(duration_ms * config.AUDIO_SAMPLE_RATE / 1000)
        t = np.linspace(0, duration_ms / 1000, sample_count)

        # Generate sine wave
        wave = np.sin(2 * np.pi * frequency * t)

        # Apply envelope to avoid clicking
        attack = int(sample_count * 0.1)
        decay = int(sample_count * 0.1)

        envelope = np.ones(sample_count)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[-decay:] = np.linspace(1, 0, decay)

        wave *= envelope * volume

        # Convert to 16-bit PCM and reshape for stereo compatibility
        wave_int16 = (wave * 32767).astype(np.int16)

        # pygame.sndarray expects (samples, channels) or (channels, samples) depending on mixer
        # For stereo mixer, we need 2D array - duplicate mono to both channels
        # Shape should be (sample_count, channels)
        wave_2d = np.column_stack([wave_int16, wave_int16])

        return wave_2d

    def play_sound(self, frequency: float, duration_ms: int):
        """Play a sound."""
        if not self.enabled or not self.is_initialized:
            return False

        try:
            sound_data = self.generate_tone(frequency, duration_ms)
            sound = pygame.sndarray.make_sound(sound_data)
            sound.play()
            return True
        except Exception as e:
            print(f"[AUDIO] ERROR: Failed to play sound: {e}")
            return False

    def play_test_beep(self):
        """Play a test beep to verify audio is working."""
        if not self.enabled or not self.is_initialized:
            if self.DEBUG:
                print("[AUDIO] Cannot play test beep: not initialized")
            return False

        try:
            # Play a pleasant 660Hz tone for 150ms
            sound_data = self.generate_tone(660, 150, 0.3)
            sound = pygame.sndarray.make_sound(sound_data)
            sound.play()
            if self.DEBUG:
                print("[AUDIO] Test beep played successfully")
            return True
        except Exception as e:
            print(f"[AUDIO] ERROR: Test beep failed: {e}")
            return False

    def update(self, risk_score: float):
        """
        Update audio based on risk score.

        Graduated feedback:
        - Safe (0-30): Silent
        - Warning (30-60): Occasional soft beep
        - Danger (60-90): Increasing frequency
        - Critical (90+): Continuous urgent tone
        """
        if not self.enabled:
            return

        self.current_risk = risk_score
        current_time = time.time()

        # Determine beep interval based on risk
        if risk_score < 30:
            beep_interval = float('inf')  # No beeps
        elif risk_score < 60:
            beep_interval = 2.0  # Every 2 seconds
        elif risk_score < 90:
            # Interpolate between 2s and 0.3s
            beep_interval = 2.0 - (risk_score - 60) * (1.7 / 30)
        else:
            beep_interval = 0.3  # Every 0.3 seconds

        # Check if we should beep
        if current_time - self.last_beep_time >= beep_interval:
            # Calculate frequency based on risk (440 Hz to 880 Hz)
            frequency = config.AUDIO_FREQ_MIN + (risk_score / 100.0) * (
                config.AUDIO_FREQ_MAX - config.AUDIO_FREQ_MIN
            )

            if self.DEBUG:
                print(f"[AUDIO] BEEP: risk={risk_score:.1f}, freq={frequency:.0f}Hz")

            self.play_sound(frequency, config.AUDIO_DURATION_MS)
            self.last_beep_time = current_time

    def play_calibration_sound(self):
        """Play calibration complete sound."""
        if not self.enabled:
            return
        self.play_sound(880, 300)  # High pitch

    def play_alert_sound(self):
        """Play danger alert sound."""
        if not self.enabled:
            return
        # Double beep for danger
        self.play_sound(880, 200)
        time.sleep(0.1)
        self.play_sound(880, 200)

    def reset(self):
        """Reset audio state."""
        self.last_beep_time = 0
        self.current_risk = 0

    def release(self):
        """Release audio resources."""
        if self.is_initialized:
            pygame.mixer.quit()
            self.is_initialized = False