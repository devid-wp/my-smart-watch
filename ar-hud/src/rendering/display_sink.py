"""Абстракция вывода. cv2.imshow сегодня, фреймбуфер AR-устройства завтра."""

from __future__ import annotations

from abc import ABC, abstractmethod

import cv2
import numpy as np


class IDisplaySink(ABC):
    """Куда уходит отрисованный кадр. Возвращает False, если пора завершать цикл."""

    @abstractmethod
    def show(self, canvas: np.ndarray) -> bool:
        """Показать кадр. False = пользователь нажал выход."""

    @abstractmethod
    def close(self) -> None:
        """Освободить ресурсы вывода. Идемпотентно."""


class OpenCVDisplaySink(IDisplaySink):
    """Стандартный вывод через cv2.imshow. Используется на дев-машине."""

    def __init__(self, window_name: str = "AR-HUD") -> None:
        self._window_name = window_name
        cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)

    def show(self, canvas: np.ndarray) -> bool:
        cv2.imshow(self._window_name, canvas)
        # waitKey(1) нужен, чтобы окно отзывалось и обрабатывало 'q'
        key = cv2.waitKey(1) & 0xFF
        return key != ord("q")

    def close(self) -> None:
        cv2.destroyWindow(self._window_name)