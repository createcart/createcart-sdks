"""Exceptions raised by the auth SDK."""


class AuthError(Exception):
    """Base class for all auth errors."""


class InvalidTokenError(AuthError):
    """The login token was missing, malformed, expired, or for the wrong app."""
