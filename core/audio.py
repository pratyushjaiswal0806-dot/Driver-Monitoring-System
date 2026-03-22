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
                # Bug fix: Properly cleanup mixer if initialization failed
                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.quit()
                except Exception:
                    pass
                self.enabled = False
                self.is_initialized = False

    def generate_tone(self, frequency: float, duration_ms: int, volume: float = 0.8) -> np.ndarray:
        """Generate a harsh tone that can wake someone up."""
        sample_count = int(duration_ms * config.AUDIO_SAMPLE_RATE / 1000)
        t = np.linspace(0, duration_ms / 1000, sample_count)

        # Generate sawtooth wave for harsher sound (more aggressive than sine)
        # Using a combination of sine + square for a jarring alert sound
        sine_wave = np.sin(2 * np.pi * frequency * t)

        # Add slight square wave component for harshness
        square_wave = np.sign(sine_wave)
        wave = 0.7 * sine_wave + 0.3 * square_wave

        # Sharp envelope - quick attack, quick decay for punchy sound
        attack = int(sample_count * 0.02)  # Very fast attack (2%)
        decay = int(sample_count * 0.15)   # Quick decay (15%)

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

    def _get_risk_level(self, risk_score: float) -> Optional[str]:
        """Determine the risk level based on score."""
        if risk_score < 20:
            return None  # Safe - no sound
        elif risk_score < 40:
            return 'mild'
        elif risk_score < 60:
            return 'warning'
        elif risk_score < 80:
            return 'high_risk'
        else:
            return 'critical'

    def _play_beep_group(self, frequency: float, duration_ms: int, count: int):
        """Play a harsh group of beeps to wake someone up."""
        # Use higher volume for waking alert
        volume = getattr(config, 'BEEP_VOLUME', 0.9)

        if self.DEBUG:
            print(
                f"[AUDIO] BEEP: {count}x, freq={frequency:.0f}Hz, dur={duration_ms}ms")

        for i in range(count):
            # Play with high volume
            sound_data = self.generate_tone(frequency, duration_ms, volume)
            try:
                sound = pygame.sndarray.make_sound(sound_data)
                sound.play()
            except Exception as e:
                print(f"[AUDIO] ERROR: Failed to play beep: {e}")

            if i < count - 1:
                # Shorter gap between beeps for urgent effect (~50ms)
                time.sleep(0.05)

    def update(self, risk_score: float):
        """
        Update audio based on risk score - simplified beeping system.

        Risk Score Levels:
        - Safe (0-20): No sound
        - Mild (20-40): Single beep every 5s
        - Warning (40-60): Double beep every 3s
        - High Risk (60-80): Triple beep every 1.5s
        - Critical (80-100): Quad beep every 0.5s
        """
        if not self.enabled:
            return

        self.current_risk = risk_score
        current_time = time.time()
        time_since_last = current_time - self.last_beep_time

        # Determine risk level and beep parameters
        if risk_score < 20:
            return  # Safe - no sound
        elif risk_score < 40:
            # Mild: 1 beep every 3s at 800Hz
            interval = 3.0
            frequency = 800
            beep_count = 1
        elif risk_score < 60:
            # Warning: 2 beeps every 1.5s at 1200Hz
            interval = 1.5
            frequency = 1200
            beep_count = 2
        elif risk_score < 80:
            # High Risk: 3 beeps every 0.8s at 1600Hz
            interval = 0.8
            frequency = 1600
            beep_count = 3
        else:
            # Critical: 4 beeps every 0.3s at 2000Hz
            interval = 0.3
            frequency = 2000
            beep_count = 4

        # Play beep if interval has passed
        if time_since_last >= interval:
            self._play_beep_group(frequency, 200, beep_count)
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
