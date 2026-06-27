"""Генерация синтетического видео для smoke-тестов и демо без камеры.

Используем cv2.VideoWriter с 'mp4v' кодеком — он встроен в opencv-python, ffmpeg не нужен.
"""

from __future__ import annotations

import os

import cv2
import numpy as np


def make_test_video(path: str, width: int = 320, height: int = 240, frames: int = 30, fps: int = 10) -> str:
    """Создаёт видео с бегущим кадром (номер в углу). Возвращает path."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, float(fps), (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Не удалось создать тестовое видео: {path}")
    for i in range(frames):
        img = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.putText(img, f"frame {i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        writer.write(img)
    writer.release()
    return path