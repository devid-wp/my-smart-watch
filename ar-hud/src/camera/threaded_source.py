"""Базовый класс для камер-источников с фоновым потоком захвата.

CameraStream и VideoFileSource наследуются отсюда, чтобы не дублировать:
- Thread + Lock для последнего кадра
- неблокирующий read()
- корректный stop()
"""

from __future__ import annotations

import threading
import time
from abc import abstractmethod

from src.core.exceptions import CameraInitError
from src.core.interfaces import Frame, ICameraSource


class _ThreadedCameraSource(ICameraSource):
    """Общая логика: фоновый поток захвата, неблокирующий read()."""

    def __init__(self) -> None:
        self._frame: Frame | None = None
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._frame_id = 0
        self._resolution: tuple[int, int] = (0, 0)
        self._stop_event = threading.Event()

    @abstractmethod
    def _open(self) -> tuple[object, tuple[int, int]]:
        """Открыть аппаратный/файловый источник. Вернуть (handle, (w, h)).

        Бросает CameraInitError, если источник не открылся.
        """

    @abstractmethod
    def _read_raw(self, handle: object) -> object | None:
        """Прочитать один кадр из handle. Вернуть None, если кадр не готов."""

    @abstractmethod
    def _close(self, handle: object) -> None:
        """Освободить ресурсы источника."""

    def start(self) -> None:
        if self._running:
            return
        handle, resolution = self._open()
        self._resolution = resolution
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop, args=(handle,), name=self.__class__.__name__, daemon=True
        )
        self._thread.start()

    def _capture_loop(self, handle: object) -> None:
        try:
            while not self._stop_event.is_set():
                raw = self._read_raw(handle)
                if raw is None:
                    # Небольшая пауза, чтобы не крутить CPU, если источник медленный
                    time.sleep(0.001)
                    continue
                self._frame_id += 1
                frame = Frame(image=raw, timestamp=time.monotonic(), frame_id=self._frame_id)
                with self._lock:
                    self._frame = frame
        finally:
            self._close(handle)

    def read(self) -> Frame | None:
        with self._lock:
            return self._frame  # Возвращаем ссылку. Frame frozen → read-only для модулей.

    def stop(self) -> None:
        if not self._running:
            return
        self._stop_event.set()
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        with self._lock:
            self._frame = None

    @property
    def resolution(self) -> tuple[int, int]:
        return self._resolution