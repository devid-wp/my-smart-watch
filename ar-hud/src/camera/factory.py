"""Фабрика ICameraSource по конфигу. Единственная точка выбора источника."""

from __future__ import annotations

from src.camera.camera_stream import CameraStream
from src.camera.video_file_source import VideoFileSource
from src.core.exceptions import CameraInitError, ConfigError
from src.core.interfaces import ICameraSource


def camera_from_config(cfg: dict) -> ICameraSource:
    """Сконструировать источник видео из cfg-секции.

    Ожидаемый формат:
        camera:
          type: webcam | file
          source: 0 | 'path/to/video.mp4'
          backend: cv2.CAP_ANY (опционально)
    """
    if "type" not in cfg:
        raise ConfigError("camera.type обязателен в конфиге")
    ctype = cfg["type"]

    if ctype == "webcam":
        return CameraStream(source=cfg.get("source", 0), backend=cfg.get("backend", -1))
    if ctype == "file":
        path = cfg.get("source")
        if not path:
            raise ConfigError("camera.source обязателен для type=file")
        return VideoFileSource(path=path)
    raise ConfigError(f"Неизвестный camera.type: {ctype!r}. Допустимо: webcam, file")