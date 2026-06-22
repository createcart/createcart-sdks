"""Mock identity provider — local dev / tests, no Google project needed.

The whole sign-in round-trip works offline: ``make_token`` builds a token the
frontend can send, and ``verify_token`` decodes it back to an Identity. A bare
``"mock"`` token yields a default demo user.
"""

from __future__ import annotations

import base64
import json

from ..exceptions import InvalidTokenError
from ..models import Identity

_PREFIX = "mock."


class MockProvider:
    name = "mock"

    @property
    def public_config(self) -> dict:
        return {"provider": self.name}

    def make_token(
        self,
        email: str = "demo@example.com",
        name: str = "Demo User",
        sub: str | None = None,
    ) -> str:
        payload = {
            "sub": sub or ("mock-" + email),
            "email": email,
            "name": name,
            "email_verified": True,
        }
        return _PREFIX + base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode()

    def verify_token(self, token: str) -> Identity:
        if not token or token == "mock":
            return Identity(
                provider=self.name, subject="mock-demo",
                email="demo@example.com", email_verified=True, name="Demo User",
            )
        if token.startswith(_PREFIX):
            try:
                data = json.loads(base64.urlsafe_b64decode(token[len(_PREFIX):]))
            except (ValueError, TypeError):
                raise InvalidTokenError("malformed mock token")
            return Identity(
                provider=self.name, subject=data["sub"], email=data.get("email"),
                email_verified=bool(data.get("email_verified", True)),
                name=data.get("name"), picture=data.get("picture"),
            )
        raise InvalidTokenError("not a mock token")
