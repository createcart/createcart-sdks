"""AuthService — verify a login token through a pluggable identity provider."""

from __future__ import annotations

from typing import Optional

from .models import Identity
from .providers.base import IdentityProvider
from .providers.mock import MockProvider


class AuthService:
    def __init__(self, provider: Optional[IdentityProvider] = None) -> None:
        self.provider = provider or MockProvider()

    @property
    def public_config(self) -> dict:
        """Non-secret config for the frontend (provider + client id)."""
        return self.provider.public_config

    def verify(self, token: str) -> Identity:
        return self.provider.verify_token(token)
