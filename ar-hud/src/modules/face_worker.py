"""Воркер детекции лиц. Живёт в отдельном процессе, чтобы обойти GIL.

Контракт обмена:
- input_q (mp.Queue, maxsize=1): кадры (numpy.ndarray) ИЛИ sentinel-словарь
  {"__slow_worker_sec__": float} — используется только тестом graceful degradation.
- output_q (mp.Queue, maxsize=1): список боксов [(x, y, w, h), ...].

Запускается один раз на старте модуля через multiprocessing.Process.
"""

from __future__ import annotations

import time

import cv2


def _load_haar() -> cv2.CascadeClassifier:
    """Haar Cascade идёт в комплекте с OpenCV — без скачивания."""
    path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    clf = cv2.CascadeClassifier(path)
    if clf.empty():
        raise RuntimeError(f"Не удалось загрузить haar cascade: {path}")
    return clf


def face_detection_worker(input_q, output_q, stop_event) -> None:  # noqa: ANN001 — multiprocessing spawn
    """Точка входа воркера. Крутится в отдельном процессе."""
    clf = _load_haar()

    while not stop_event.is_set():
        try:
            payload = input_q.get(timeout=0.1)
        except Exception:  # noqa: BLE001 — queue.Empty / OSError при завершении
            continue

        if payload is None:
            continue

        # Sentinel от теста: замедлить воркер
        if isinstance(payload, dict) and "__slow_worker_sec__" in payload:
            time.sleep(float(payload["__slow_worker_sec__"]))
            continue

        gray = cv2.cvtColor(payload, cv2.COLOR_BGR2GRAY)
        detections = clf.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        boxes = [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in detections]

        # Публикуем результат, дропая старый если очередь занята
        try:
            output_q.put_nowait(boxes)
        except Exception:  # noqa: BLE001 — Queue.Full
            try:
                output_q.get_nowait()
                output_q.put_nowait(boxes)
            except Exception:  # noqa: BLE001
                pass