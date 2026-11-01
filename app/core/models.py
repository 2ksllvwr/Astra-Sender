from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MessageTask:
    id: Optional[int]
    profile_id: int
    message: str
    scheduled_at: datetime
    mode: str = 'write'  # 'write' ou 'click'
    recurrence: str = 'once'  # 'once', 'daily' ou 'weekly'
    status: str = 'pending'
