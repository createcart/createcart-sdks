"""Notify models."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class NotificationResult(BaseModel):
    """The outcome of one send attempt."""

    provider: str
    to: str
    channel: str = "sms"           # "sms" | "whatsapp"
    status: str = "sent"           # provider status, or "logged" / "failed"
    sid: Optional[str] = None      # provider message id
    error: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict)
