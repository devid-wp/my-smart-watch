"""Общие примитивы рисования. Стиль и цвета — в одном месте."""

from __future__ import annotations

import cv2
import numpy as np


# Базовые цвета HUD-а (BGR — OpenCV-порядок)
COLOR_TEXT = (0, 255, 0)
COLOR_ACCENT = (255, 255, 0)
COLOR_PANEL_BG = (0, 0, 0)
COLOR_FACE_BOX = (0, 200, 255)

FONT = cv2.FONT_HERSHEY_SIMPLEX


def draw_panel(canvas: np.ndarray, x: int, y: int, w: int, h: int) -> None:
    """Чёрная полупрозрачная подложка под текст."""
    overlay = canvas.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), COLOR_PANEL_BG, -1)
    # 0.6 = коэффициент прозрачности; 1.0 = полностью непрозрачный
    cv2.addWeighted(overlay, 0.6, canvas, 0.4, 0, canvas)


def draw_text(canvas: np.ndarray, text: str, pos: tuple[int, int], scale: float = 0.55, color: tuple[int, int, int] = COLOR_TEXT, thickness: int = 1) -> None:
    cv2.putText(canvas, text, pos, FONT, scale, color, thickness)


def draw_box(canvas: np.ndarray, box: tuple[int, int, int, int], color: tuple[int, int, int] = COLOR_FACE_BOX, thickness: int = 2) -> None:
    """Рисует прямоугольник по (x, y, w, h). Если x<0 — клипа по canvas не делаем."""
    x, y, w, h = box
    cv2.rectangle(canvas, (x, y), (x + w, y + h), color, thickness)