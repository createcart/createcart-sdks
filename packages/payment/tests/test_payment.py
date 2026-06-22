import pytest

from createcart_payment import (
    MockProvider,
    PaymentService,
    PaymentStatus,
    RazorpayProvider,
    SignatureVerificationError,
)
from createcart_payment.storage import InMemoryPaymentStore, JSONFilePaymentStore


def test_mock_create_order():
    svc = PaymentService(MockProvider())
    order = svc.create_order(25000, receipt="r-1")
    assert order.id.startswith("order_")
    assert order.amount == 25000
    assert order.provider == "mock"
    assert order.status == PaymentStatus.created


def test_mock_full_round_trip_with_store():
    provider = MockProvider()
    store = InMemoryPaymentStore()
    svc = PaymentService(provider, store=store)
    order = svc.create_order(13000, cart_id="sess-1")
    assert store.get(order.id).status == PaymentStatus.created

    pay = provider.make_test_payment(order.id)  # server-side valid pair
    record = svc.verify_payment(order.id, pay["payment_id"], pay["signature"])
    assert record.status == PaymentStatus.paid
    assert record.payment_id == pay["payment_id"]
    assert record.cart_id == "sess-1"
    assert store.get(order.id).status == PaymentStatus.paid


def test_bad_signature_raises_and_marks_failed():
    provider = MockProvider()
    store = InMemoryPaymentStore()
    svc = PaymentService(provider, store=store)
    order = svc.create_order(5000)
    with pytest.raises(SignatureVerificationError):
        svc.verify_payment(order.id, "pay_x", "deadbeef")
    assert store.get(order.id).status == PaymentStatus.failed


def test_razorpay_signature_scheme():
    # Verify the documented HMAC scheme without hitting the network.
    import hashlib
    import hmac

    provider = RazorpayProvider("rzp_test_key", "secret123")
    order_id, payment_id = "order_abc", "pay_xyz"
    good = hmac.new(b"secret123", f"{order_id}|{payment_id}".encode(),
                    hashlib.sha256).hexdigest()
    assert provider.verify_signature(order_id, payment_id, good) is True
    assert provider.verify_signature(order_id, payment_id, "nope") is False


def test_razorpay_requires_keys():
    from createcart_payment import ProviderError

    with pytest.raises(ProviderError):
        RazorpayProvider("", "")


def test_public_key_exposed():
    assert PaymentService(MockProvider(key_id="mock_abc")).public_key == "mock_abc"


def test_jsonfile_store_round_trip(tmp_path):
    provider = MockProvider()
    svc = PaymentService(provider, store=JSONFilePaymentStore(tmp_path))
    order = svc.create_order(9900, cart_id="sess-9")
    pay = provider.make_test_payment(order.id)
    svc.verify_payment(order.id, pay["payment_id"], pay["signature"])

    # New service instance, same dir -> sees the paid record.
    svc2 = PaymentService(provider, store=JSONFilePaymentStore(tmp_path))
    rec = svc2.store.get(order.id)
    assert rec.status == PaymentStatus.paid
    assert rec.amount == 9900


def test_jsonfile_rejects_unsafe_order_id(tmp_path):
    store = JSONFilePaymentStore(tmp_path)
    with pytest.raises(ValueError):
        store.get("../escape")
