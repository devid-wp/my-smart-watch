"""Захват с веб-камеры или произвольного cv2-источника (RTSP, V4L2, etc)."""

from __future__ import annotations

import cv2
import numpy as np

from src.camera.threaded_source import _ThreadedCameraSource
from src.core.exceptions import CameraInitError


class CameraStream(_ThreadedCameraSource):
    """ICameraSource поверх cv2.VideoCapture.

    Захват идёт в отдельном потоке — read() неблокирующий, всегда возвращает
    последний снятый кадр (или None, если ещё ничего не снято).
    """

    def __init__(self, source: int | str = 0, backend: int = cv2.CAP_ANY) -> None:
        super().__init__()
        self._source = source
        self._backend = backend
        self._cap: cv2.VideoCapture | None = None

    def _open(self) -> tuple[cv2.VideoCapture, tuple[int, int]]:
        cap = cv2.VideoCapture(self._source, self._backend)
        if not cap.isOpened():
            cap.release()
            raise CameraInitError(
                f"Не удалось открыть видеоисточник: {self._source!r}. "
                f"Проверьте подключение камеры / права доступа."
            )
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._cap = cap
        return cap, (w, h)

    def _read_raw(self, handle: cv2.VideoCapture) -> np.ndarray | None:
        ok, image = handle.read()
        if not ok or image is None:
            return None
        return image

    def _close(self, handle: cv2.VideoCapture) -> None:
        handle.release()
        self._cap = None