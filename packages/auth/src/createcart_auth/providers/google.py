"""Google "Sign in with Google" provider.

Verifies a Google ID token (JWT) via Google's ``tokeninfo`` endpoint — Google
checks the signature and expiry; we additionally enforce the **audience**
(our OAuth client id) and **issuer**. No google-auth / JWT dependency.

For very high volume you'd cache Google's JWKS and verify the JWT locally; the
``_validate`` step here is the security-critical part and is unit-tested.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from ..exceptions import AuthError, InvalidTokenError
from ..models import Identity

_TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"
_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleProvider:
    name = "google"

    def __init__(self, client_id: str, *, timeout: float = 10.0) -> None:
        if not client_id:
            raise AuthError("GoogleProvider requires a client_id")
        self.client_id = client_id
        self._timeout = timeout

    @property
    def public_config(self) -> dict:
        return {"provider": self.name, "client_id": self.client_id}

    def verify_token(self, token: str) -> Identity:
        if not token:
            raise InvalidTokenError("missing token")
        url = _TOKENINFO + "?" + urllib.parse.urlencode({"id_token": token})
        try:
            with urllib.request.urlopen(url, timeout=self._timeout) as resp:
                claims = json.loads(resp.read().decode())
        except urllib.error.HTTPError:  # pragma: no cover - network
            raise InvalidTokenError("Google rejected the token")
        except urllib.error.URLError as exc:  # pragma: no cover - network
            raise AuthError(f"Google unreachable: {exc.reason}")

        self._validate(claims)
        return Identity(
            provider=self.name,
            subject=claims["sub"],
            email=claims.get("email"),
            email_verified=str(claims.get("email_verified")).lower() == "true",
            name=claims.get("name"),
            picture=claims.get("picture"),
        )

    def _validate(self, claims: dict) -> None:
        if claims.get("aud") != self.client_id:
            raise InvalidTokenError("token audience does not match this app")
        if claims.get("iss") not in _ISSUERS:
            raise InvalidTokenError("unexpected token issuer")
        exp = claims.get("exp")
        if exp is not None and int(exp) < int(time.time()):
            raise InvalidTokenError("token expired")
        if "sub" not in claims:
            raise InvalidTokenError("token missing subject")
