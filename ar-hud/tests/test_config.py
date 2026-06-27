"""Тесты config/loader.py и schema.py."""

from __future__ import annotations

import pytest
import yaml

from config.loader import load_config
from config.schema import AppConfig
from src.core.exceptions import ConfigError


def _write(tmp_path, body: str) -> str:
    p = tmp_path / "cfg.yaml"
    p.write_text(body, encoding="utf-8")
    return str(p)


def test_default_yaml_loads(tmp_path):
    """default.yaml валиден и собирается в AppConfig."""
    default = "C:/Users/galas/OneDrive/Desktop/my smart watch/ar-hud/config/default.yaml"
    cfg = load_config(default)
    assert isinstance(cfg, AppConfig)
    assert cfg.camera.type == "file"
    assert any(m.type == "clock" for m in cfg.modules)


def test_duplicate_module_names_rejected(tmp_path):
    path = _write(
        tmp_path,
        yaml.safe_dump(
            {
                "camera": {"type": "webcam", "source": 0},
                "modules": [
                    {"type": "clock", "name": "dup"},
                    {"type": "system_monitor", "name": "dup"},
                ],
            }
        ),
    )
    with pytest.raises(ConfigError, match="не прошёл валидацию"):
        load_config(path)


def test_unknown_camera_type_rejected(tmp_path):
    path = _write(
        tmp_path,
        yaml.safe_dump({"camera": {"type": "rtsp"}}),
    )
    with pytest.raises(ConfigError, match="не прошёл валидацию"):
        load_config(path)


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(ConfigError, match="Конфиг не найден"):
        load_config(tmp_path / "does_not_exist.yaml")


def test_invalid_yaml_raises(tmp_path):
    path = _write(tmp_path, "camera: : :")
    with pytest.raises(ConfigError, match="Невалидный YAML"):
        load_config(path)


def test_top_level_must_be_mapping(tmp_path):
    path = _write(tmp_path, "- just\n- a\n- list\n")
    with pytest.raises(ConfigError, match="мапой"):
        load_config(path)