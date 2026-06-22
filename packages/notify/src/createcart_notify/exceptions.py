"""Exceptions raised by the notify SDK."""


class NotifyError(Exception):
    """Base class for all notify errors."""


class ProviderError(NotifyError):
    """The upstream provider (e.g. Twilio) returned an error."""
