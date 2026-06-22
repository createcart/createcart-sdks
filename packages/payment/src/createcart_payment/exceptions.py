"""Exceptions raised by the payment SDK."""


class PaymentError(Exception):
    """Base class for all payment errors."""


class ProviderError(PaymentError):
    """The upstream provider (e.g. Razorpay) returned an error."""


class SignatureVerificationError(PaymentError):
    """A payment's signature did not verify — possible tampering."""
