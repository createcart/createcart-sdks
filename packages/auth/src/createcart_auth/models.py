"""Auth models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Identity(BaseModel):
    """A verified end-user identity."""

    provider: str                 # "google" | "mock" | ...
    subject: str                  # stable unique user id (Google "sub")
    email: Optional[str] = None
    email_verified: bool = False
    name: Optional[str] = None
    picture: Optional[str] = None
