"""Adaptador para o mecanismo de mouse do engine."""
from .base import AutomationProvider
from .engine import _mouse


class PyAutoGuiProvider(AutomationProvider):
    def send(self, profile: dict, message: str | None, mode: str) -> str:
        return _mouse(profile, message or '', mode)
