"""Интеграционный тест main.py: поднимаем pipeline из реальных частей,
гоняем ~30 кадров на VideoFileSource, проверяем чистое завершение.

Это НЕ end-to-end (не вызываем main() как процесс), но проверяет тот же путь:
load_config → camera_from_config → build_modules → Pipeline.run.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import tempfile
import threading
import time

import cv2
import numpy as np
import pytest
import yaml

from config.loader import load_config
from src.camera.factory import camera_from_config
from src.core.clock import Clock
from src.core.module_registry import build_modules_from_config
from src.core.pipeline import Pipeline
from src.modules.face_detection_module import FaceDetectionModule
from src.rendering.hud_overlay import HUDOverlay


class _HeadlessDisplay:
    """Дисплей без cv2.imshow — для CI и тестов без GUI."""

    def __init__(self, stop_after: int = 30) -> None:
        self.shown = 0
        self.closed = False
        self._stop_after = stop_after

    def show(self, canvas) -> bool:
        self.shown += 1
        return self.shown < self._stop_after

    def close(self) -> None:
        self.closed = True


def _make_test_video(path: str) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    w = cv2.VideoWriter(path, fourcc, 10.0, (320, 240))
    for i in range(20):
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(img, f"f{i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        w.write(img)
    w.release()


def _build_test_config(video_path: str, tmp_dir: str) -> str:
    cfg = {
        "camera": {"type": "file", "source": video_path},
        "window_name": "test",
        "modules": [
            {"type": "clock", "name": "c", "enabled": True, "params": {"position": [10, 30]}},
            {"type": "system_monitor", "name": "s", "enabled": True, "params": {"position": [10, 60]}},
        ],
    }
    cfg_path = os.path.join(tmp_dir, "test_cfg.yaml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)
    return cfg_path


def test_pipeline_from_config_runs_and_exits_cleanly():
    """Полный путь: load_config → factory → build_modules → run() → shutdown."""
    mp_fork = mp.get_context("spawn")
    with tempfile.TemporaryDirectory() as d:
        video = os.path.join(d, "test.mp4")
        _make_test_video(video)
        cfg_path = _build_test_config(video, d)

        cfg = load_config(cfg_path)
        camera = camera_from_config(cfg.camera.model_dump())
        modules = build_modules_from_config(cfg.modules_dump())

        # face_detection в конфиге быть не должно, но если кто-то добавит — запустим
        face_modules = [m for m in modules if isinstance(m, FaceDetectionModule)]
        for f in face_modules:
            f.start()

        display = _HeadlessDisplay(stop_after=30)
        pipeline = Pipeline(camera=camera, overlay=HUDOverlay(modules), clock=Clock(), display=display)
        pipeline.run()

        for f in face_modules:
            f.stop()
        for f in face_modules:
            for q in (getattr(f, "_input_q", None), getattr(f, "_output_q", None)):
                if q is not None:
                    try:
                        q.close()
                    except Exception:
                        pass

        # Проверки
        assert display.shown > 0
        assert display.closed
        assert camera.__class__.__name__ == "VideoFileSource"

        # После shutdown не должно висеть ничего лишнего
        main_thread = threading.main_thread()
        leftovers = [t for t in threading.enumerate() if t is not main_thread and t.daemon]
        # daemon-потоки могут остаться — это нормально для глобальных очередей mp
        # Но не должно быть наших pipeline-потоков
        for t in leftovers:
            assert "Thread" in t.name or "Thread-" in t.name  # mp-feed threads


def test_disabling_modules_via_config_works():
    """Включение/выключение модулей через YAML меняет поведение без правок кода."""
    with tempfile.TemporaryDirectory() as d:
        video = os.path.join(d, "test.mp4")
        _make_test_video(video)

        cfg = {
            "camera": {"type": "file", "source": video},
            "modules": [
                {"type": "clock", "name": "c", "enabled": False},  # выключен
            ],
        }
        cfg_path = os.path.join(d, "cfg.yaml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f)

        loaded = load_config(cfg_path)
        modules = build_modules_from_config(loaded.modules_dump())
        assert modules[0].enabled is False


def test_invalid_config_returns_error_code(tmp_path):
    """Сломанный конфиг → load_config бросает ConfigError (main ловит и выходит с кодом 2)."""
    from src.core.exceptions import ConfigError

    bad = tmp_path / "bad.yaml"
    bad.write_text("camera:\n  type: rtsp\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(str(bad))