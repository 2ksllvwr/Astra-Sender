"""Adaptador para o mecanismo UI Automation do Windows."""
from .base import AutomationProvider
from .engine import _uia


class WindowsUIAProvider(AutomationProvider):
    def send(self, profile: dict, message: str | None, mode: str) -> str:
        return _uia(profile, message or '', mode)
