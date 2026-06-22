"""Identity providers. Implement :class:`IdentityProvider` to add a login method."""

from .base import IdentityProvider
from .google import GoogleProvider
from .mock import MockProvider

__all__ = ["IdentityProvider", "GoogleProvider", "MockProvider"]
