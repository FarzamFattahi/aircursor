from __future__ import annotations

from aircursor.gestures import (
    DragAction,
    DragController,
    InteractionMode,
    PinchDetector,
    PinchState,
)
from aircursor.models import DetectedHand, Point
from aircursor.pointer import CoordinateMapper, OneEuroFilter, TapStabilizer


def make_hand(pinch_distance: float = 0.2) -> DetectedHand:
    points = [Point(0.5, 0.5) for _ in range(21)]
    points[0] = Point(0.5, 0.8)
    points[4] = Point(0.4, 0.3)
    points[8] = Point(0.4 + pinch_distance, 0.3)
    points[5] = Point(0.3, 0.6)
    points[17] = Point(0.7, 0.6)
    return DetectedHand(tuple(points), "Right", 0.99)


def test_coordinate_mapper_clamps_and_expands_control_area() -> None:
    mapper = CoordinateMapper(1920, 1080, margin_x=0.1, margin_y=0.1)
    assert mapper.map(0.1, 0.1) == (0, 0)
    assert mapper.map(0.9, 0.9) == (1919, 1079)
    assert mapper.map(-1.0, 2.0) == (0, 1079)


def test_pinch_detector_uses_confirmation_and_hysteresis() -> None:
    detector = PinchDetector(confirm_frames=2, release_frames=2)
    assert detector.update(0.2) is PinchState.PINCH_CANDIDATE
    assert detector.update(0.2) is PinchState.PINCHED
    assert detector.update(0.4) is PinchState.PINCHED
    assert detector.update(0.6) is PinchState.RELEASE_CANDIDATE
    assert detector.update(0.6) is PinchState.OPEN


def test_short_pinch_clicks_and_long_pinch_drags() -> None:
    drag = DragController(hold_seconds=0.5)
    assert drag.pinch_started(1.0) is DragAction.NONE
    assert drag.pinch_released(1.2) is DragAction.CLICK
    drag.pinch_started(2.0)
    assert drag.tick(2.6) is DragAction.BUTTON_DOWN
    assert drag.pinch_released(2.7) is DragAction.BUTTON_UP


def test_one_euro_filter_initializes_and_smooths() -> None:
    smoother = OneEuroFilter(min_cutoff=1.0, beta=0.0)
    assert smoother.filter((0.0, 0.0), 1.0) == (0.0, 0.0)
    x, y = smoother.filter((100.0, 100.0), 1.01)
    assert 0.0 < x < 100.0
    assert x == y


def test_tap_stabilizer_holds_anchor_during_click_window() -> None:
    stabilizer = TapStabilizer(double_tap_window=0.4)
    assert stabilizer.stabilize((10.0, 20.0), InteractionMode.PINCH, 1.0) == (10.0, 20.0)
    assert stabilizer.stabilize(
        (14.0, 25.0), InteractionMode.POINTER, 1.1, tap_completed=True
    ) == (10.0, 20.0)
    assert stabilizer.stabilize((15.0, 30.0), InteractionMode.POINTER, 1.6) == (15.0, 30.0)


def test_detected_hand_requires_complete_landmarks() -> None:
    try:
        DetectedHand((Point(0.0, 0.0),), "Right", 1.0)
    except ValueError as error:
        assert "21 landmarks" in str(error)
    else:
        raise AssertionError("Incomplete landmarks should be rejected")


def test_normalized_pinch_distance_uses_palm_scale() -> None:
    from aircursor.gestures import normalized_pinch_distance

    hand = make_hand(pinch_distance=0.2)
    assert abs(normalized_pinch_distance(hand) - 0.5) < 1e-9
