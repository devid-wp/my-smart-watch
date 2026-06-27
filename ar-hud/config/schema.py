"""Pydantic-схема конфига. Валидация на старте, чтобы YAML не падал в середине рендера."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CameraConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["webcam", "file"]
    source: int | str = 0
    backend: int = -1


class ModuleEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    name: str
    enabled: bool = True
    params: dict[str, object] = Field(default_factory=dict)


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera: CameraConfig
    modules: list[ModuleEntry] = Field(default_factory=list)
    window_name: str = "AR-HUD"

    @field_validator("modules")
    @classmethod
    def _unique_module_names(cls, v: list[ModuleEntry]) -> list[ModuleEntry]:
        names = [m.name for m in v]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Дублирующиеся modules[*].name: {sorted(duplicates)}")
        return v

    def modules_dump(self) -> list[dict]:
        """Список dict'ов в формате, который ждёт build_modules_from_config."""
        return [m.model_dump() for m in self.modules]