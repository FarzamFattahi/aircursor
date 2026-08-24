from __future__ import annotations

from .models import DetectedHand, Point


class MediaPipeHandDetector:
    """Small adapter that keeps MediaPipe outside the reusable gesture layer."""

    def __init__(self, max_num_hands: int = 2) -> None:
        try:
            from mediapipe.python.solutions import hands as mp_hands
        except ImportError as error:
            raise RuntimeError("Install AirCursor dependencies before using the camera") from error
        self._hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=0.65,
            min_tracking_confidence=0.60,
        )

    def process(self, frame_bgr: object) -> list[DetectedHand]:
        import cv2

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self._hands.process(rgb)
        detected: list[DetectedHand] = []
        for landmarks, handedness in zip(
            result.multi_hand_landmarks or [],
            result.multi_handedness or [],
            strict=True,
        ):
            classification = handedness.classification[0]
            detected.append(
                DetectedHand(
                    landmarks=tuple(
                        Point(point.x, point.y, point.z) for point in landmarks.landmark
                    ),
                    handedness=classification.label,
                    confidence=float(classification.score),
                )
            )
        return detected

    def close(self) -> None:
        self._hands.close()

