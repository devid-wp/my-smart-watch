"""
Clock — единственный источник dt во всём проекте.

Зачем:
- Централизует замер времени (time.monotonic, не wall-clock).
- Защищает от NameError на первом тике (явная инициализация _last_time = None).
- Защищает от "телепорта" анимаций после паузы/брейкпоинта (max_dt clamp).
"""

from __future__ import annotations

import time


class Clock:
    """Монотонные часы с защитой от скачков.

    Использование:
        clock = Clock()
        while running:
            dt = clock.tick()
            ...
    """

    def __init__(self, max_dt: float = 0.1) -> None:
        """max_dt — порог в секундах. Реальный dt выше порога обрезается.

        0.1s = 10 FPS минимум; ниже этого считаем, что была пауза.
        """
        self._last_time: float | None = None
        self.dt: float = 0.0
        self.max_dt: float = max_dt

    def tick(self) -> float:
        """Продвигает часы на один кадр. Возвращает dt в секундах.

        Первый вызов возвращает 0.0 (нет предыдущего замера — нет и дельты).
        Последующие — clamp(min(real_dt, max_dt)).
        """
        now = time.monotonic()
        if self._last_time is None:
            self.dt = 0.0
        else:
            self.dt = min(now - self._last_time, self.max_dt)
        self._last_time = now
        return self.dt

    def reset(self) -> None:
        """Сбросить часы (например, после паузы отладчика)."""
        self._last_time = None
        self.dt = 0.0