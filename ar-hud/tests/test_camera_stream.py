"""Тесты для src/camera/.

Покрывает:
- VideoFileSource: 50-кадровый smoke-test на синтетическом видео.
- factory: парсинг конфига webcam/file, ошибка на неизвестный тип.
- CameraInitError: понятное сообщение, если файл не существует.
- Мок cv2.VideoCapture для CameraStream (без реального устройства).
"""

from __future__ import annotations

import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.camera.factory import camera_from_config
from src.camera.video_file_source import VideoFileSource
from src.core.exceptions import CameraInitError, ConfigError
from tests._make_test_video import make_test_video


def test_video_file_source_smoke_50_frames():
    """Phase 0 acceptance: захват 50 кадров с тестового видеофайла без падений."""
    with tempfile.TemporaryDirectory() as d:
        path = make_test_video(os.path.join(d, "test.mp4"), frames=30)
        src = VideoFileSource(path=path)
        try:
            src.start()
            # ждём, пока поток захвата доберётся до первого кадра
            deadline = time.monotonic() + 5.0
            while src.read() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            assert src.read() is not None, "первый кадр так и не пришёл"
            assert src.resolution == (320, 240)
            # читаем 50 кадров подряд, ни один не должен бросить
            seen = 0
            t0 = time.monotonic()
            while seen < 50 and time.monotonic() - t0 < 10.0:
                f = src.read()
                if f is not None:
                    seen += 1
                else:
                    time.sleep(0.01)
            assert seen >= 50, f"собрано только {seen} кадров за 10с"
        finally:
            src.stop()


def test_video_file_source_missing_file_raises_camera_init_error():
    """Отсутствующий файл → CameraInitError с понятным сообщением, не FileNotFoundError."""
    src = VideoFileSource(path="Z:/nonexistent/path/that/never/exists.mp4")
    with pytest.raises(CameraInitError, match="Не удалось открыть видеофайл"):
        src.start()


def test_video_file_source_stop_is_idempotent():
    """Повторный stop() не должен бросать и не должен оставлять поток."""
    with tempfile.TemporaryDirectory() as d:
        path = make_test_video(os.path.join(d, "test.mp4"), frames=5)
        src = VideoFileSource(path=path)
        src.start()
        time.sleep(0.2)
        src.stop()
        src.stop()  # второй раз не должен падать


def test_factory_webcam():
    cam = camera_from_config({"type": "webcam", "source": 0})
    assert cam.__class__.__name__ == "CameraStream"


def test_factory_file():
    cam = camera_from_config({"type": "file", "source": "foo.mp4"})
    assert cam.__class__.__name__ == "VideoFileSource"


def test_factory_unknown_type_raises_config_error():
    with pytest.raises(ConfigError, match="Неизвестный camera.type"):
        camera_from_config({"type": "rtsp"})


def test_factory_missing_type_raises_config_error():
    with pytest.raises(ConfigError, match="camera.type обязателен"):
        camera_from_config({})


def test_factory_file_requires_source():
    with pytest.raises(ConfigError, match="camera.source обязателен"):
        camera_from_config({"type": "file"})


def test_camera_stream_with_mocked_capture():
    """CameraStream читает кадры через мок cv2.VideoCapture, без реального устройства."""
    from src.camera.camera_stream import CameraStream

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.get.side_effect = lambda prop: {  # CAP_PROP_FRAME_WIDTH/HEIGHT
        3: 640.0,  # CAP_PROP_FRAME_WIDTH
        4: 480.0,  # CAP_PROP_FRAME_HEIGHT
    }.get(prop, 0.0)
    fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cap.read.return_value = (True, fake_frame)

    with patch("src.camera.camera_stream.cv2.VideoCapture", return_value=mock_cap):
        cam = CameraStream(source=0)
        cam.start()
        try:
            deadline = time.monotonic() + 3.0
            f = None
            while time.monotonic() < deadline:
                f = cam.read()
                if f is not None:
                    break
                time.sleep(0.05)
            assert f is not None
            assert f.image.shape == (480, 640, 3)
            assert cam.resolution == (640, 480)
        finally:
            cam.stop()
        mock_cap.release.assert_called()