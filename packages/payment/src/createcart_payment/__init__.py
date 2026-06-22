"""CreateCart Payment SDK.

A pluggable payment layer. Providers implement a small interface
(:class:`PaymentProvider`); a Razorpay provider and a Mock provider ship in the
box. The :class:`PaymentService` ties a provider to optional record storage.

Flow (Razorpay-style)::

    service.create_order(amount_minor=25000)        # -> PaymentOrder (server)
    # ... browser pays via the provider's checkout widget ...
    service.verify_payment(order_id, payment_id, signature)   # -> PaymentRecord
"""

from .exceptions import (
    PaymentError,
    ProviderError,
    SignatureVerificationError,
)
from .models import PaymentOrder, PaymentRecord, PaymentStatus
from .providers import MockProvider, PaymentProvider, RazorpayProvider
from .service import PaymentService

__all__ = [
    "PaymentService",
    "PaymentProvider",
    "RazorpayProvider",
    "MockProvider",
    "PaymentOrder",
    "PaymentRecord",
    "PaymentStatus",
    "PaymentError",
    "ProviderError",
    "SignatureVerificationError",
]

__version__ = "0.1.0"
