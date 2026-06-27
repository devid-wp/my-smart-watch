"""Базовый класс с общей заглушкой enabled/name/params."""

from __future__ import annotations

from src.core.interfaces import Frame, IHUDModule


class AbstractHUDModule(IHUDModule):
    """Снимает с модулей рутину: name, enabled, приём params из конфига.

    Конкретный модуль переопределяет update() и render(). Если нужно — ещё __init__,
    чтобы распаковать специфичные params (см. SystemMonitorModule).
    """

    def __init__(self, name: str, enabled: bool = True, **params: object) -> None:
        self.name = name
        self.enabled = enabled
        self._params = params

    def update(self, frame: Frame, dt: float) -> None:
        """Заглушка. Модуль без состояния может не переопределять."""

    def render(self, canvas) -> None:  # noqa: ANN001 - numpy.ndarray в .pyi, тут сознательно без аннотации
        """Заглушка. Модуль без визуала может не переопределять."""