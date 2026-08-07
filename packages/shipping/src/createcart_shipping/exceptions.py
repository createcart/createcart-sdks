class ShippingError(Exception):
    """A shipping provider call failed (network, auth, bad response)."""


class NotServiceableError(ShippingError):
    """The destination pincode can't be shipped to — don't call rate/create for it."""


class ShipmentCreationError(ShippingError):
    """The provider rejected the manifest (bad address, missing warehouse, etc.)."""


class ShipmentNotFoundError(ShippingError):
    """No shipment exists for that waybill."""
