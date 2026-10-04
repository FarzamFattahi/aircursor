from test_core import make_hand

from aircursor.gestures import GestureManager, InteractionMode
from aircursor.interaction import FrameInputController
from aircursor.pointer import TapStabilizer


class Recorder:
    def __init__(self):
        self.events = []

    def move(self, x, y):
        self.events.append(("move", x, y))

    def click(self):
        self.events.append(("click",))

    def left_down(self):
        self.events.append(("down",))

    def left_up(self):
        self.events.append(("up",))

    def release_all(self):
        self.events.append(("release",))

    def scroll(self, amount):
        self.events.append(("scroll", amount))


def test_click_is_sent_after_position_and_drag_starts_on_anchor():
    native = Recorder()
    controller = FrameInputController(native)
    controller.move(100, 200)
    controller.click()
    assert native.events == [("move", 100, 200)]
    controller.move(100, 200)
    assert native.events[-2:] == [("move", 100, 200), ("click",)]
    controller.left_down()
    controller.move(140, 240)
    assert native.events[-3:] == [("move", 100, 200), ("down",), ("move", 140, 240)]
    controller.left_up()
    controller.move(160, 260)
    assert native.events[-2:] == [("move", 160, 260), ("up",)]


def test_late_second_pinch_uses_new_target_and_closing_uses_previous_target():
    stabilizer = TapStabilizer(0.5)
    stabilizer.stabilize((100, 200), InteractionMode.POINTER, 0)
    assert stabilizer.stabilize((120, 220), InteractionMode.PINCH, 0.1) == (100, 200)
    stabilizer.stabilize((130, 230), InteractionMode.POINTER, 0.2, True)
    # Open-hand movement resumes on the next frame: no wait for another tap.
    assert stabilizer.stabilize((110, 210), InteractionMode.POINTER, 0.25) == (110, 210)
    # Fast second pinch is anchored to exactly the same pixel.
    assert stabilizer.stabilize((140, 240), InteractionMode.PINCH, 0.6) == (100, 200)
    stabilizer.stabilize((300, 400), InteractionMode.POINTER, 0.8)
    assert stabilizer.stabilize((310, 410), InteractionMode.PINCH, 0.9) == (300, 400)


def test_release_candidate_at_drag_boundary_remains_click():
    native = Recorder()
    manager = GestureManager(native, drag_hold_ms=520, scrolling=False)
    closed, opened = make_hand(0.05), make_hand(0.3)
    manager.update(closed, 0)
    manager.update(closed, 0.03)
    manager.update(opened, 0.55)
    result = manager.update(opened, 0.58)
    assert result.tap_completed
    assert native.events == [("click",)]


def test_tracking_loss_cancels_pending_click_and_requires_open_hand():
    native = Recorder()
    controller = FrameInputController(native)
    manager = GestureManager(controller, scrolling=False)
    closed, opened = make_hand(0.05), make_hand(0.3)
    manager.update(closed, 0)
    manager.update(closed, 0.03)
    manager.reset()
    for now in (0.1, 0.2, 0.8):
        assert manager.update(closed, now).mode is InteractionMode.POINTER
    assert controller.pending == []
    manager.update(opened, 0.9)
    manager.update(closed, 1)
    manager.update(closed, 1.03)
    manager.update(opened, 1.1)
    manager.update(opened, 1.13)
    controller.move(10, 20)
    assert native.events[-2:] == [("move", 10, 20), ("click",)]


def test_drag_has_one_down_and_loss_always_releases():
    native = Recorder()
    controller = FrameInputController(native)
    manager = GestureManager(controller, scrolling=False)
    closed = make_hand(0.05)
    for now in (0, 0.03, 0.6, 0.7, 0.8):
        manager.update(closed, now)
        controller.move(100, 200)
    assert native.events.count(("down",)) == 1
    assert ("click",) not in native.events
    manager.reset()
    assert native.events[-1] == ("release",)


def test_two_natural_taps_emit_two_complete_clicks_never_a_held_button():
    native = Recorder()
    controller = FrameInputController(native)
    manager = GestureManager(controller, scrolling=False)
    closed, opened = make_hand(0.05), make_hand(0.17)
    for now, hand, position in (
        (0.0, closed, (100, 200)), (0.03, closed, (100, 200)),
        (0.16, opened, (100, 200)), (0.19, opened, (100, 200)),
        (0.24, closed, (130, 225)), (0.27, closed, (130, 225)),
        (0.40, opened, (130, 225)), (0.43, opened, (130, 225)),
    ):
        controller.clock = lambda current=now: current
        manager.update(hand, now)
        controller.move(*position)
    assert native.events.count(("click",)) == 2
    assert ("down",) not in native.events
    assert native.events[-2:] == [("move", 100, 200), ("click",)]


def test_an_ordinary_half_second_pinch_does_not_start_drag():
    native = Recorder()
    manager = GestureManager(native, scrolling=False)
    closed, opened = make_hand(0.05), make_hand(0.17)
    for now in (0, 0.03, 0.3, 0.55):
        manager.update(closed, now)
    manager.update(opened, 0.58)
    manager.update(opened, 0.61)
    assert native.events == [("click",)]


def test_moving_wrist_to_another_target_does_not_snap_second_click():
    native = Recorder()
    controller = FrameInputController(native)
    controller.clock = lambda: 0
    controller.set_hand_intent(0.5, 0.5)
    controller.click()
    controller.move(100, 200)
    controller.clock = lambda: 0.2
    controller.set_hand_intent(0.65, 0.5)
    controller.click()
    controller.move(400, 500)
    assert native.events[-2:] == [("move", 400, 500), ("click",)]
