"""The contract every identity provider implements."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import Identity


@runtime_checkable
class IdentityProvider(Protocol):
    name: str

    @property
    def public_config(self) -> dict:
        """Non-secret config the frontend needs (e.g. the OAuth client id)."""
        ...

    def verify_token(self, token: str) -> Identity:
        """Verify a login token and return the user's :class:`Identity`."""
        ...
