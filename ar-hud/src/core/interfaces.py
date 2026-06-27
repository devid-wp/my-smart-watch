"""
Базовые интерфейсы ядра. Не зависят от OpenCV-захвата или конкретных модулей.

Правила:
- IHUDModule: только вычисления в update(), только отрисовка в render().
- ICameraSource.read() неблокирующий: может вернуть None.
- Frame.timestamp — monotonic time, НЕ wall-clock.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Frame:
    """Снимок видеопотока + метаданные для синхронизации модулей.

    frozen=True защищает от случайной мутации модулем (кадр read-only).
    """

    image: np.ndarray
    timestamp: float  # time.monotonic()
    frame_id: int


class ICameraSource(ABC):
    """Абстракция источника видео. Замена webcam → file → RTSP без правки ядра."""

    @abstractmethod
    def start(self) -> None:
        """Открыть источник и запустить фоновый захват. Бросает CameraInitError."""

    @abstractmethod
    def read(self) -> Frame | None:
        """Неблокирующее чтение последнего кадра. None, если кадр ещё не готов."""

    @abstractmethod
    def stop(self) -> None:
        """Корректно остановить источник и освободить ресурсы. Идемпотентно."""

    @property
    @abstractmethod
    def resolution(self) -> tuple[int, int]:
        """(width, height) источника. До start() может возвращать (0, 0)."""


class IHUDModule(ABC):
    """Интерфейс одного модуля HUD. Архитектурный контракт:

    - update(frame, dt): ТОЛЬКО вычисления. Никакого рисования, никакого IO.
    - render(canvas):      ТОЛЬКО отрисовка на переданном canvas. Никаких вычислений/IO.

    Это разделение позволяет в будущем развести частоту логики и частоту дисплея.
    """

    name: str
    enabled: bool

    @abstractmethod
    def update(self, frame: Frame, dt: float) -> None:
        """Обновить внутреннее состояние. dt в секундах."""

    @abstractmethod
    def render(self, canvas: np.ndarray) -> None:
        """Отрисовать себя на canvas (in-place). canvas не должен менять размер."""