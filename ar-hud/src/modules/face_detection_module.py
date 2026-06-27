"""FaceDetectionModule: детекция лиц в отдельном процессе.

update() неблокирующе отдаёт кадр в воркер через Queue(maxsize=1) и забирает
последний готовый результат. Если воркер не успевает — рисуем то, что было на
прошлом кадре. FPS видео не зависит от скорости детекции (graceful degradation).
"""

from __future__ import annotations

import multiprocessing as mp
import time
from multiprocessing.synchronize import Event as MpEvent
from multiprocessing.queues import Queue as MpQueue

from src.core.interfaces import Frame
from src.core.module_registry import register_module
from src.modules.base_module import AbstractHUDModule
from src.modules.face_worker import face_detection_worker
from src.rendering.draw_utils import draw_box


@register_module("face_detection")
class FaceDetectionModule(AbstractHUDModule):
    def __init__(
        self,
        name: str = "face_detection",
        enabled: bool = False,
        model: str = "haarcascade",
        **kwargs,
    ) -> None:
        super().__init__(name=name, enabled=enabled, **kwargs)
        self._model = model

        self._input_q: MpQueue | None = None
        self._output_q: MpQueue | None = None
        self._stop_event: MpEvent | None = None
        self._process: mp.Process | None = None
        self._last_boxes: list[tuple[int, int, int, int]] = []

    def start(self) -> None:
        """Запустить воркер-процесс. Вызывается из pipeline перед run()."""
        ctx = mp.get_context("spawn")
        self._input_q = ctx.Queue(maxsize=1)
        self._output_q = ctx.Queue(maxsize=1)
        self._stop_event = ctx.Event()
        self._process = ctx.Process(
            target=face_detection_worker,
            args=(self._input_q, self._output_q, self._stop_event),
            name="face-detection-worker",
            daemon=True,
        )
        self._process.start()
        # Дождаться фактического старта воркера. На Windows mp.Queue под spawn
        # использует фоновый feed-thread, и put_nowait до старта воркера
        # иногда зависает.
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if self._process.is_alive():
                # Короткая пауза, чтобы воркер успел дойти до input_q.get()
                time.sleep(0.05)
                return
            time.sleep(0.01)
        raise RuntimeError("face detection worker не стартовал за 3 секунды")

    def stop(self) -> None:
        """Остановить воркер. Идемпотентно."""
        if self._stop_event is not None:
            self._stop_event.set()
        if self._process is not None:
            self._process.join(timeout=2.0)
            if self._process.is_alive():
                self._process.terminate()
                # НЕ вызываем join повторно после terminate — на Windows это
                # иногда приводит к зависанию в join_thread() очередей ниже.
                # Просто отдаём управление. Daemon-процесс умрёт с родителем.
            self._process = None
        # Закрываем очереди аккуратно: close() без join_thread().
        # join_thread() на Windows в Python 3.14 может зависнуть бесконечно,
        # если процесс был terminate'нут. SkipThread на свой страх.
        for q in (self._input_q, self._output_q):
            if q is not None:
                try:
                    q.close()
                except Exception:  # noqa: BLE001
                    pass

    def send_slowdown_signal(self, sec: float) -> None:
        """Служебный метод для теста graceful degradation: воркер замедлится на sec секунд.

        Не использовать в прод-коде.
        """
        if self._input_q is None:
            return
        try:
            self._input_q.put_nowait({"__slow_worker_sec__": sec})
        except Exception:  # noqa: BLE001
            pass

    def update(self, frame: Frame, dt: float) -> None:
        if self._input_q is None or self._output_q is None:
            return

        # send (неблокирующий, дроп если занято)
        try:
            self._input_q.put_nowait(frame.image)
        except Exception:  # noqa: BLE001 — Queue.Full
            try:
                self._input_q.get_nowait()
            except Exception:  # noqa: BLE001
                pass
            try:
                self._input_q.put_nowait(frame.image)
            except Exception:  # noqa: BLE001
                pass

        # receive (неблокирующий, оставляем прошлый результат если нового нет)
        try:
            self._last_boxes = self._output_q.get_nowait()
        except Exception:  # noqa: BLE001 — Queue.Empty
            pass

    def render(self, canvas) -> None:
        for box in self._last_boxes:
            draw_box(canvas, box)