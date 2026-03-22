"""Driver Monitoring System - Main Entry Point."""

from calibration.driver_profile import DriverProfile
from calibration.calibrator import Calibrator, CalibrationStatus
from core.audio import AudioManager
from core.display import DisplayManager
from core.detector import DetectionOrchestrator
from core.camera import Camera
from core.logbook import LogbookManager, AlertLog
from core.health_analyzer import HealthAnalyzer
from detectors import EyeState
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
    print("\nOptions:")
    print("  [1] Quick Start (skip calibration)")
    print("  [2] Calibrate")
    print("  [Q] Quit")
    print("\nWaiting for input...\n")

    while True:
        menu_frame = display.create_menu_frame()
        display.show(menu_frame)

        key = display.get_key()

        if key == ord('1'):
            print("Starting inference...")
            return 'quick'
        elif key == ord('2'):
            print("Starting calibration...")
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

    # Initialize logbook
    logbook = None
    if config.LOGBOOK_ENABLED:
        logbook = LogbookManager(
            config.LOGBOOK_DB_PATH,
            auto_cleanup_days=config.LOGBOOK_AUTO_CLEANUP_DAYS
        )
        print("Logbook initialized")

    # Initialize health analyzer
    health_analyzer = None
    if config.HEALTH_ANALYZER_ENABLED and config.LOGBOOK_ENABLED:
        health_analyzer = HealthAnalyzer(config.LOGBOOK_DB_PATH)
        print("Health Analyzer initialized")

    # Start camera
    print("Initializing camera...")
    if not camera.start():
        print("Failed to start camera!")
        display.release()
        if logbook:
            logbook.release()
        return 1

    print(f"Camera: {camera.get_resolution()} @ {camera.get_fps():.1f} FPS\n")

    # Show startup menu
    choice = show_startup_menu(display)

    if choice == 'quit':
        print("Exiting...")
        camera.release()
        display.release()
        if logbook:
            logbook.release()
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
    print(
        "Press [Q] to quit, [C] to recalibrate, [L] for logbook stats, [E] to export")
    print("-" * 60 + "\n")

    running = True
    last_time = time.time()
    last_cleanup_time = time.time()
    fps_counter = 0

    # Track risk level for logging
    last_risk_level = None
    last_logged_timestamp = time.time()
    logged_component = None

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

            # Determine current risk level
            current_risk_level = None
            if detections.risk_score.total < 20:
                current_risk_level = 'SAFE'
            elif detections.risk_score.total < 40:
                current_risk_level = 'MILD'
            elif detections.risk_score.total < 60:
                current_risk_level = 'WARNING'
            elif detections.risk_score.total < 80:
                current_risk_level = 'HIGH'
            else:
                current_risk_level = 'CRITICAL'

            # Log alerts on risk level change
            if logbook and current_risk_level != 'SAFE':
                if current_risk_level != last_risk_level:
                    try:
                        # Determine which component triggered the alert
                        triggered_by = "multiple"
                        if detections.risk_score.phone_score > 50:
                            triggered_by = "phone_detection"
                        elif detections.eye_result and detections.eye_result.state == EyeState.CLOSED:
                            triggered_by = "eyes_closed"
                        elif detections.risk_score.drowsy_score > 50:
                            triggered_by = "drowsiness"
                        elif detections.risk_score.attention_score > 50:
                            triggered_by = "looking_away"

                        alert = AlertLog(
                            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                            risk_level=current_risk_level,
                            risk_score=detections.risk_score.total,
                            triggered_by=triggered_by
                        )
                        logbook.log_alert(alert)
                        logged_component = triggered_by
                    except Exception as e:
                        print(f"Warning: Failed to log alert: {e}")

            last_risk_level = current_risk_level

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

            # Periodic cleanup of old logs
            if logbook:
                try:
                    # Run cleanup every ~5 minutes
                    if current_time - last_cleanup_time > 300:
                        logbook.clear_old_logs()
                        last_cleanup_time = current_time
                except Exception as e:
                    print(f"Warning: Cleanup error: {e}")

        # Show logbook stats overlay if enabled
        if config.LOGBOOK_SHOW_GUI_STATS and logbook:
            try:
                stats = logbook.get_today_statistics()
                y_pos = display.height - 80
                cv2.putText(display_frame, f"Today: {stats['total']} alerts - "
                            f"M:{stats['MILD']} W:{stats['WARNING']} "
                            f"H:{stats['HIGH']} C:{stats['CRITICAL']} "
                            f"[L] for details",
                            (10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            config.COLOR_INFO, 1)
            except Exception as e:
                print(f"Warning: Failed to render logbook stats: {e}")

        # Display the frame
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
        elif key == config.KEY_LOGBOOK_CONSOLE and logbook:
            # Print detailed console statistics
            print()  # New line for formatting
            logbook.print_console_stats(days=7)
        elif key == config.KEY_LOGBOOK_EXPORT and logbook:
            # Export to CSV
            export_path = time.strftime('alerts_%Y%m%d_%H%M%S.csv')
            if logbook.export_to_csv(export_path):
                print(f"Exported to {export_path}")
            else:
                print(f"Failed to export to {export_path}")
        elif key == config.KEY_HEALTH_REPORT and health_analyzer:
            # Print health analysis report
            print()  # New line for formatting
            print(health_analyzer.get_health_report(
                days=config.HEALTH_ANALYSIS_DAYS))
            print()  # New line for formatting

    # Cleanup
    print("\nShutting down...")
    camera.release()
    audio.release()
    orchestrator.release()
    display.release()

    if logbook:
        # Final cleanup
        logbook.clear_old_logs()
        logbook.release()
        print("Logbook saved and closed")

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
