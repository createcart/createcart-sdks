import pytest

from createcart_notify import (
    ConsoleProvider,
    NotifyService,
    ProviderError,
    TwilioProvider,
)


def test_console_provider_records():
    p = ConsoleProvider()
    svc = NotifyService(p, business_name="Brahmana Naivedyam")
    res = svc.notify_status("+9198000", "out_for_delivery", name="Asha",
                            order_id="order_abcdef123456")
    assert res.status == "logged"
    assert p.sent[0]["to"] == "+9198000"
    assert "out for delivery" in p.sent[0]["text"]
    assert "Brahmana Naivedyam" in p.sent[0]["text"]
    assert "#123456" in p.sent[0]["text"]   # last 6 of order id


def test_no_phone_is_noop():
    p = ConsoleProvider()
    svc = NotifyService(p)
    assert svc.notify_status(None, "placed") is None
    assert svc.notify_status("", "placed") is None
    assert p.sent == []


def test_message_for_each_status():
    svc = NotifyService(ConsoleProvider(), business_name="Biz")
    for status in ["placed", "confirmed", "preparing", "out_for_delivery",
                   "delivered", "cancelled"]:
        msg = svc.message_for(status, name="A", order_id="order_x12345")
        assert "Biz" in msg and msg


def test_unknown_status_has_fallback_message():
    svc = NotifyService(ConsoleProvider())
    assert "weird" in svc.message_for("weird", order_id="order_x12345")


def test_whatsapp_channel_passthrough():
    p = ConsoleProvider()
    NotifyService(p).notify_status("+9198", "delivered", channel="whatsapp")
    assert p.sent[0]["channel"] == "whatsapp"


def test_twilio_requires_credentials():
    with pytest.raises(ProviderError):
        TwilioProvider("", "")


def test_twilio_requires_from_for_channel():
    # configured for sms only -> whatsapp send raises before any network call
    t = TwilioProvider("AC_sid", "token", from_sms="+1555")
    with pytest.raises(ProviderError):
        t.send("+9198", "hi", channel="whatsapp")
