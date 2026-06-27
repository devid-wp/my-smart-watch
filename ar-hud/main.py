"""Точка входа ar-hud.

По правилу #1 из плана: никакой бизнес-логики здесь. Только:
  1. Загрузить и валидировать конфиг
  2. Собрать пайплайн
  3. Запустить
  4. Обработать корректное завершение
"""

from __future__ import annotations

import argparse
import logging
import multiprocessing as mp
import signal
import sys
import threading

from config.loader import load_config
from src.camera.factory import camera_from_config
from src.core.clock import Clock
from src.core.exceptions import CameraInitError, ConfigError
from src.core.module_registry import build_modules_from_config
from src.core.pipeline import Pipeline
from src.modules.face_detection_module import FaceDetectionModule
from src.rendering.display_sink import OpenCVDisplaySink
from src.rendering.hud_overlay import HUDOverlay
from src.utils.logging_setup import setup_logging


logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="ar-hud")
    p.add_argument(
        "--config",
        default="config/default.yaml",
        help="Путь к YAML-конфигу (default: config/default.yaml)",
    )
    p.add_argument("--log-level", default="INFO", help="DEBUG/INFO/WARNING/ERROR")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    setup_logging(args.log_level)

    # multiprocessing под Windows требует __main__ guard для spawn
    if __name__ != "__main__":
        return 0
    mp.freeze_support()

    # 1. Конфиг
    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        logger.error(f"Конфиг сломан: {e}")
        return 2

    logger.info(
        f"Запуск: camera={cfg.camera.type}, modules={[m.name for m in cfg.modules]}"
    )

    # 2. Сборка пайплайна
    try:
        camera = camera_from_config(cfg.camera.model_dump())
    except CameraInitError as e:
        logger.error(f"Камера: {e}")
        return 3

    modules = build_modules_from_config(cfg.modules_dump())
    # Стартуем модули, которым нужен отдельный процесс (сейчас только face_detection)
    for m in modules:
        if isinstance(m, FaceDetectionModule):
            m.start()

    overlay = HUDOverlay(modules)
    clock = Clock()
    display = OpenCVDisplaySink(window_name=cfg.window_name)
    pipeline = Pipeline(camera=camera, overlay=overlay, clock=clock, display=display)

    # 3. Ctrl+C → корректный shutdown. На Windows SIGINT в главном потоке
    # обычно сам прерывает cv2.waitKey(), но на случай headless — перехватим явно.
    def _on_sigint(signum, frame):  # noqa: ANN001
        logger.info("Получен SIGINT, останавливаемся...")
        pipeline.stop()

    signal.signal(signal.SIGINT, _on_sigint)

    # 4. Запуск
    try:
        pipeline.run()
    except Exception as e:  # noqa: BLE001
        logger.exception(f"Pipeline упал: {e}")
        return 1
    finally:
        for m in modules:
            if isinstance(m, FaceDetectionModule):
                m.stop()
        _check_no_orphans()
    return 0


def _check_no_orphans() -> None:
    """Graceful shutdown: после возврата не должно висеть потоков/процессов."""
    leftover_threads = [t for t in threading.enumerate() if t is not threading.main_thread()]
    leftover_procs = mp.active_children()
    if leftover_threads:
        logger.warning(f"Остались потоки: {[t.name for t in leftover_threads]}")
    if leftover_procs:
        logger.warning(f"Остались процессы: {[p.name for p in leftover_procs]}")


if __name__ == "__main__":
    sys.exit(main())