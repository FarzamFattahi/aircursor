from __future__ import annotations

import argparse
import ctypes
import time

from .config import AirCursorConfig
from .gestures import GestureManager, InteractionMode, pinch_midpoint
from .hand_selector import HandSelector
from .input import WindowsInputController
from .interaction import FrameInputController
from .pointer import CoordinateMapper, OneEuroFilter, PointerGain, TapStabilizer
from .vision import MediaPipeHandDetector


def emergency_stop_pressed() -> bool:
    if not hasattr(ctypes, "windll"):
        return False
    key_down = ctypes.windll.user32.GetAsyncKeyState
    return bool(key_down(0x11) & 0x8000 and key_down(0x12) & 0x8000 and key_down(0x1B) & 0x8000)


def run(config: AirCursorConfig) -> None:
    import cv2

    config.validate()
    native_input = WindowsInputController()
    input_controller = FrameInputController(native_input)
    width, height = input_controller.screen_size()
    mapper = CoordinateMapper(width, height, config.margin_x, config.margin_y)
    smoother = OneEuroFilter(config.min_cutoff, config.beta, config.derivative_cutoff)
    gain = PointerGain(config.pointer_gain)
    stabilizer = TapStabilizer(native_input.double_click_time())
    selector = HandSelector(config.preferred_hand)
    gestures = GestureManager(input_controller, config.drag_hold_ms, config.scroll_enabled)
    detector = MediaPipeHandDetector()

    capture = cv2.VideoCapture(config.camera_index, cv2.CAP_DSHOW)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not capture.isOpened():
        detector.close()
        raise RuntimeError("Camera unavailable or already in use")

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError("The camera stopped responding")
            if config.mirror_preview:
                frame = cv2.flip(frame, 1)

            now = time.monotonic()
            hands = detector.process(frame)
            hand = selector.select(hands)
            mode = InteractionMode.TRACKING_LOST

            if hand is None:
                gestures.reset()
                smoother.reset()
                gain.reset()
                stabilizer.reset()
            else:
                result = gestures.update(hand, now)
                mode = result.mode
                if mode in {InteractionMode.POINTER, InteractionMode.PINCH, InteractionMode.DRAG}:
                    point = pinch_midpoint(hand)
                    screen_point = mapper.map(*point)
                    screen_point = smoother.filter(screen_point, now)
                    screen_point = gain.apply(screen_point)
                    screen_point = stabilizer.stabilize(
                        screen_point, mode, now, result.tap_completed
                    )
                    input_controller.move(round(screen_point[0]), round(screen_point[1]))

                for landmark in hand.landmarks:
                    cv2.circle(
                        frame,
                        (int(landmark.x * frame.shape[1]), int(landmark.y * frame.shape[0])),
                        3,
                        (100, 230, 190),
                        -1,
                    )

            left = int(config.margin_x * frame.shape[1])
            right = int((1.0 - config.margin_x) * frame.shape[1])
            top = int(config.margin_y * frame.shape[0])
            bottom = int((1.0 - config.margin_y) * frame.shape[0])
            cv2.rectangle(frame, (left, top), (right, bottom), (130, 220, 90), 2)
            cv2.putText(
                frame,
                f"AirCursor | {mode.name} | Q or Ctrl+Alt+Esc to stop",
                (16, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (240, 240, 240),
                1,
                cv2.LINE_AA,
            )
            cv2.imshow("AirCursor Open Source", frame)
            if cv2.waitKey(1) & 0xFF in {ord("q"), 27} or emergency_stop_pressed():
                break
    finally:
        gestures.reset()
        input_controller.release_all()
        detector.close()
        capture.release()
        cv2.destroyAllWindows()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control the Windows pointer with one hand")
    parser.add_argument("--camera", type=int, default=0, help="OpenCV camera index")
    parser.add_argument("--hand", choices=("Auto", "Left", "Right"), default="Auto")
    parser.add_argument("--drag-hold-ms", type=int, default=650)
    parser.add_argument("--no-scroll", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run(
        AirCursorConfig(
            camera_index=args.camera,
            preferred_hand=args.hand,
            drag_hold_ms=args.drag_hold_ms,
            scroll_enabled=not args.no_scroll,
        )
    )


if __name__ == "__main__":
    main()

