"""Driver Monitoring System - Main Entry Point."""

from calibration.driver_profile import DriverProfile
from calibration.calibrator import Calibrator, CalibrationStatus
from core.audio import AudioManager
from core.display import DisplayManager
from core.detector import DetectionOrchestrator
from core.camera import Camera
import config
import sys
import time
import cv2

# Add project to path
sys.path.insert(0, 'C:/Users/praty/driver_monitor')


def show_startup_menu(display: DisplayManager) -> str:
    """Show startup menu and get user choice."""
    print("\n" + "=" * 50)
    print("  DRIVER MONITORING SYSTEM")
    print("=" * 50)

    while True:
        menu_frame = display.create_menu_frame()
        display.show(menu_frame)

        key = display.get_key()

        if key == ord('1'):
            return 'quick'
        elif key == ord('2'):
            return 'calibrate'
        elif key == config.KEY_QUIT:
            return 'quit'


def run_calibration(display: DisplayManager,
                    orchestrator: DetectionOrchestrator,
                    calibrator: Calibrator,
                    camera: Camera) -> bool:
    """Run calibration phase."""
    print("\nStarting calibration...")
    print(f"Duration: {config.CALIBRATION_DURATION_SEC} seconds")
    print("Please sit normally and look at the camera.\n")

    calibrator.start()
    profile_generated = False

    while not calibrator.is_complete() and not calibrator.is_failed():
        ret, frame = camera.read()
        if not ret:
            print("Camera error during calibration")
            return False

        # Process frame for detections
        detections = orchestrator.process_frame(frame)

        # Update calibration
        status, progress, time_remaining = calibrator.process_frame(
            frame,
            eye_result=detections.eye_result,
            mouth_result=detections.mouth_result,
            head_pose=detections.head_pose
        )

        # Render calibration screen
        display_frame = display.render_calibration(
            frame, progress, time_remaining)
        display.show(display_frame)

        key = display.get_key()
        if key == config.KEY_QUIT:
            return False

    # Generate profile
    profile = calibrator.generate_profile("default")
    if profile and profile.is_calibrated:
        orchestrator.set_profile(profile)
        profile.save()
        print(f"\nCalibration complete!")
        print(f"  EAR mean: {profile.ear_mean:.3f}")
        print(f"  MAR mean: {profile.mar_mean:.3f}")
        return True
    else:
        print("\nCalibration failed, using defaults")
        return False


def main():
    """Main application loop."""
    print("\n" + "=" * 60)
    print("  AI Driver Monitoring System")
    print("  Real-time drowsiness & distraction detection")
    print("=" * 60 + "\n")

    # Initialize components
    camera = Camera()
    orchestrator = DetectionOrchestrator(use_yolo=True)
    display = DisplayManager(config.FRAME_WIDTH, config.FRAME_HEIGHT)
    audio = AudioManager()
    calibrator = Calibrator()

    # Start camera
    print("Initializing camera...")
    if not camera.start():
        print("Failed to start camera!")
        display.release()
        return 1

    print(f"Camera: {camera.get_resolution()} @ {camera.get_fps():.1f} FPS\n")

    # Show startup menu
    choice = show_startup_menu(display)

    if choice == 'quit':
        print("Exiting...")
        camera.release()
        display.release()
        return 0

    calibrated = False

    if choice == 'calibrate':
        calibrated = run_calibration(display, orchestrator, calibrator, camera)

    # Load profile if exists and not just calibrated
    if not calibrated and not config.CALIBRATION_OPTIONAL:
        if orchestrator.load_default_profile():
            print("Loaded existing calibration")
            calibrated = True

    if not calibrated:
        print("Using default thresholds")

    print("\n" + "-" * 60)
    print("Starting monitoring...")
    print("Press [Q] to quit, [C] to recalibrate")
    print("-" * 60 + "\n")

    running = True
    last_time = time.time()
    fps_counter = 0

    while running:
        # Read frame
        ret, frame = camera.read()
        if not ret:
            print("Camera read error")
            break

        # Process frame
        detections = orchestrator.process_frame(frame)

        # Update audio
        if detections.risk_score:
            audio.update(detections.risk_score.total)

        # Render
        display_frame = display.render(
            frame,
            risk_score=detections.risk_score,
            detections=detections.to_dict(),
            landmarks=detections.face_data.landmarks if detections.face_data else None
        )

        # Show FPS
        current_time = time.time()
        fps_counter += 1
        if current_time - last_time >= 1.0:
            cv2.putText(display_frame, f"FPS: {fps_counter}",
                        (10, display.height - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        config.COLOR_NEUTRAL, 1)
            fps_counter = 0
            last_time = current_time

        display.show(display_frame)

        # Handle input
        key = display.get_key()
        if key == config.KEY_QUIT:
            running = False
        elif key == config.KEY_TEST_BEEP:
            print("\nPlaying test beep...")
            audio.play_test_beep()
        elif key == config.KEY_CALIBRATE:
            print("\nRecalibrating...")
            display.show(display.create_waiting_frame())
            calibrated = run_calibration(
                display, orchestrator, calibrator, camera)

    # Cleanup
    print("\nShutting down...")
    camera.release()
    audio.release()
    orchestrator.release()
    display.release()

    # Print stats
    stats = orchestrator.get_stats()
    print(f"\nSession stats:")
    print(f"  Frames: {stats['frames_processed']}")
    print(f"  Face detection rate: {stats['face_detection_rate']:.1%}")

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
