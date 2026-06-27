"""Источник видео из файла. Используется для smoke-тестов и демо без камеры."""

from __future__ import annotations

import cv2
import numpy as np

from src.camera.threaded_source import _ThreadedCameraSource
from src.core.exceptions import CameraInitError


class VideoFileSource(_ThreadedCameraSource):
    """Читает кадры из видеофайла. Когда файл кончается — крутится по кругу.

    По кругу — намеренно: smoke-test и демо должны идти бесконечно, пока не нажмёшь 'q'.
    """

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path
        self._cap: cv2.VideoCapture | None = None

    def _open(self) -> tuple[cv2.VideoCapture, tuple[int, int]]:
        cap = cv2.VideoCapture(self._path)
        if not cap.isOpened():
            cap.release()
            raise CameraInitError(f"Не удалось открыть видеофайл: {self._path!r}")
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._cap = cap
        return cap, (w, h)

    def _read_raw(self, handle: cv2.VideoCapture) -> np.ndarray | None:
        ok, image = handle.read()
        if ok and image is not None:
            return image
        # Файл кончился — перематываем в начало
        handle.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, image = handle.read()
        return image if ok else None

    def _close(self, handle: cv2.VideoCapture) -> None:
        handle.release()
        self._cap = None