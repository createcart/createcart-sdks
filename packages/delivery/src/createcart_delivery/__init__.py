"""CreateCart Delivery SDK.

Tracks an order through its lifecycle as a validated state machine:

    placed → confirmed → preparing → out_for_delivery → delivered
    (any non-terminal state → cancelled)

Every transition is recorded in a timeline the customer can track.

    from createcart_delivery import DeliveryService
    svc = DeliveryService()
    order = svc.create_order(items=[...], customer={"name": "A", "phone": "9..."})
    svc.advance(order.id)          # placed -> confirmed
    svc.track(order.id)            # status + timeline
"""

from .exceptions import (
    DeliveryError,
    DeliveryNotFoundError,
    InvalidTransitionError,
)
from .models import (
    Courier,
    Customer,
    DeliveryOrder,
    DeliveryStatus,
    OrderItem,
    StatusEvent,
)
from .service import DeliveryService

__all__ = [
    "DeliveryService",
    "DeliveryOrder",
    "DeliveryStatus",
    "Customer",
    "OrderItem",
    "Courier",
    "StatusEvent",
    "DeliveryError",
    "DeliveryNotFoundError",
    "InvalidTransitionError",
]

__version__ = "0.1.0"
