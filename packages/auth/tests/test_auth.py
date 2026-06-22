import time

import pytest

from createcart_auth import (
    AuthError,
    AuthService,
    GoogleProvider,
    InvalidTokenError,
    MockProvider,
)


def test_mock_default_demo_user():
    svc = AuthService(MockProvider())
    ident = svc.verify("mock")
    assert ident.provider == "mock"
    assert ident.email == "demo@example.com"
    assert ident.name == "Demo User"


def test_mock_make_and_verify_token_round_trip():
    p = MockProvider()
    token = p.make_token(email="asha@gmail.com", name="Asha")
    ident = p.verify_token(token)
    assert ident.email == "asha@gmail.com"
    assert ident.name == "Asha"
    assert ident.subject == "mock-asha@gmail.com"


def test_mock_bad_token():
    with pytest.raises(InvalidTokenError):
        MockProvider().verify_token("not-a-mock-token")


def test_public_config():
    assert MockProvider().public_config == {"provider": "mock"}
    cfg = GoogleProvider("abc.apps.googleusercontent.com").public_config
    assert cfg == {"provider": "google", "client_id": "abc.apps.googleusercontent.com"}


def test_google_requires_client_id():
    with pytest.raises(AuthError):
        GoogleProvider("")


def test_google_claim_validation():
    g = GoogleProvider("my-client-id")
    base = {"sub": "123", "iss": "accounts.google.com",
            "exp": int(time.time()) + 600, "aud": "my-client-id"}
    g._validate(base)  # ok

    with pytest.raises(InvalidTokenError):       # wrong audience (token for another app)
        g._validate({**base, "aud": "someone-else"})
    with pytest.raises(InvalidTokenError):       # bad issuer
        g._validate({**base, "iss": "evil.com"})
    with pytest.raises(InvalidTokenError):       # expired
        g._validate({**base, "exp": int(time.time()) - 10})
    with pytest.raises(InvalidTokenError):       # missing subject
        g._validate({k: v for k, v in base.items() if k != "sub"})
