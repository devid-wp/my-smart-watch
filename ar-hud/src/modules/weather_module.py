"""WeatherModule: погода с внешнего API, обновление раз в N секунд.

Реальный HTTP-вызов НЕ делается на каждом кадре: запросы уходят в фоне через
простой worker-thread, в основной цикл приходит только последний результат.
Без сети / API-ключа модуль просто показывает "n/a" — не падает.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.parse
import urllib.request
from dataclasses import dataclass

import cv2

from src.core.interfaces import Frame
from src.core.module_registry import register_module
from src.modules.base_module import AbstractHUDModule


@dataclass
class _WeatherSnapshot:
    text: str
    valid: bool


@register_module("weather")
class WeatherModule(AbstractHUDModule):
    def __init__(
        self,
        name: str = "weather",
        enabled: bool = True,
        api_key_env: str = "WEATHER_API_KEY",
        city: str = "Moscow",
        refresh_interval_sec: float = 600.0,
        position: tuple[int, int] = (20, 200),
        **kwargs,
    ) -> None:
        super().__init__(name=name, enabled=enabled, **kwargs)
        self._api_key = os.environ.get(api_key_env, "")
        self._city = city
        self._interval = refresh_interval_sec
        self._position = position
        self._since_update = 0.0
        self._snapshot = _WeatherSnapshot(text="weather: n/a", valid=False)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        if self._api_key:
            self._thread = threading.Thread(target=self._worker, name="weather", daemon=True)
            self._thread.start()

    def _worker(self) -> None:
        while not self._stop_event.is_set():
            snap = self._fetch()
            with self._lock:
                self._snapshot = snap
            # спим, но просыпаемся по стоп-сигналу
            self._stop_event.wait(self._interval)

    def _fetch(self) -> _WeatherSnapshot:
        """OpenWeatherMap current weather. Без ключа — сразу n/a."""
        if not self._api_key:
            return _WeatherSnapshot(text="weather: no API key", valid=False)
        try:
            qs = urllib.parse.urlencode({"q": self._city, "appid": self._api_key, "units": "metric"})
            url = f"https://api.openweathermap.org/data/2.5/weather?{qs}"
            with urllib.request.urlopen(url, timeout=5.0) as resp:  # noqa: S310 — внешний API
                payload = json.loads(resp.read().decode("utf-8"))
            temp = payload["main"]["temp"]
            desc = payload["weather"][0]["description"]
            return _WeatherSnapshot(text=f"{self._city}: {temp:.0f}C {desc}", valid=True)
        except Exception:  # noqa: BLE001 — сетевой модуль, не должен ронять приложение
            return _WeatherSnapshot(text=f"{self._city}: err", valid=False)

    def update(self, frame: Frame, dt: float) -> None:
        # Никаких вычислений здесь — render читает атомарный snapshot под lock
        return

    def render(self, canvas) -> None:
        with self._lock:
            text = self._snapshot.text
        x, y = self._position
        cv2.putText(
            canvas,
            text,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (200, 200, 255),
            1,
        )

    def stop(self) -> None:
        """Остановить фоновый worker (graceful shutdown)."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None