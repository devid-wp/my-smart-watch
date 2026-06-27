"""Acceptance Phase 4: при принудительном замедлении тяжёлого модуля основной FPS не падает.

Идея:
1. Прогон pipeline с включённым FaceDetectionModule без замедления → замеряем fps_main.
2. Прогон pipeline с включённым FaceDetectionModule + slowdown_signal → замеряем fps_main_slow.
3. Проверяем, что fps_main_slow >= 0.7 * fps_main (падение < 30%).
   На Windows со spawn-процессом есть оверхед на старт, но steady-state должен
   работать.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import numpy as np

from src.core.clock import Clock
from src.core.interfaces import Frame, ICameraSource
from src.core.module_registry import register_module
from src.core.pipeline import Pipeline
from src.modules.base_module import AbstractHUDModule
from src.modules.face_detection_module import FaceDetectionModule
from src.rendering.hud_overlay import HUDOverlay


class _FastCamera(ICameraSource):
    def __init__(self, n: int = 200) -> None:
        self._n = n
        self._i = 0

    def start(self) -> None:
        return

    def read(self) -> Frame | None:
        if self._i >= self._n:
            return None
        self._i += 1
        return Frame(
            image=np.zeros((240, 320, 3), dtype=np.uint8),
            timestamp=time.monotonic(),
            frame_id=self._i,
        )

    def stop(self) -> None:
        return

    @property
    def resolution(self):
        return (320, 240)


class _NoopDisplay:
    def __init__(self, stop_after: int) -> None:
        self.shown = 0
        self.closed = False
        self._stop_after = stop_after

    def show(self, canvas) -> bool:
        self.shown += 1
        return self.shown < self._stop_after

    def close(self) -> None:
        self.closed = True


def _measure_pipeline_fps(n_frames: int, slowdown_sec: float = 0.0):
    cam = _FastCamera(n=n_frames)
    face = FaceDetectionModule(name="face", enabled=True)
    face.start()
    try:
        if slowdown_sec > 0:
            face.send_slowdown_signal(slowdown_sec)

        disp = _NoopDisplay(stop_after=n_frames)
        overlay = HUDOverlay([face])
        pipe = Pipeline(camera=cam, overlay=overlay, clock=Clock(), display=disp)
        t0 = time.perf_counter()
        pipe.run()
        elapsed = time.perf_counter() - t0
        return disp.shown / elapsed if elapsed > 0 else float("inf")
    finally:
        face.stop()


def test_graceful_degradation_fps_drop_under_threshold():
    """Основной FPS видео не должен падать больше чем на 30% при медленном воркере.

    Реальный порог может быть другим — этот тест фиксирует контракт. Если на
    конкретной машине падение больше, ищем в чём затык.
    """
    N = 100

    fps_fast = _measure_pipeline_fps(N, slowdown_sec=0.0)
    fps_slow = _measure_pipeline_fps(N, slowdown_sec=0.05)

    # FPS slow не должен упасть ниже 70% от FPS fast
    assert fps_slow >= 0.7 * fps_fast, (
        f"graceful degradation нарушен: fast={fps_fast:.1f} FPS, "
        f"slow={fps_slow:.1f} FPS, падение {(1 - fps_slow/fps_fast)*100:.1f}%"
    )


def test_face_worker_process_exits_on_stop():
    """После face.stop() воркер-процесс не висит."""
    import multiprocessing as mp

    before = len(mp.active_children())
    face = FaceDetectionModule(name="face", enabled=True)
    face.start()
    time.sleep(0.5)  # дать воркеру время подняться
    assert len(mp.active_children()) > before
    face.stop()
    # ждём завершения до 3 секунд
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and len(mp.active_children()) > before:
        time.sleep(0.1)
    assert len(mp.active_children()) == before, "воркер не завершился после stop()"