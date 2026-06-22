"""Payment providers.

Implement :class:`PaymentProvider` to add a gateway (Stripe, Cashfree, …)
without touching the service or app code.
"""

from .base import PaymentProvider
from .mock import MockProvider
from .razorpay import RazorpayProvider

__all__ = ["PaymentProvider", "RazorpayProvider", "MockProvider"]
