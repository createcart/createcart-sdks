"""CreateCart Auth SDK.

Pluggable customer identity. Providers verify a login token and return an
:class:`Identity`. A Google provider (Sign in with Google) and a Mock provider
(local dev / tests, no Google project) ship in the box.

    from createcart_auth import AuthService, GoogleProvider
    auth = AuthService(GoogleProvider(client_id="...apps.googleusercontent.com"))
    identity = auth.verify(id_token)        # -> Identity(email, name, subject, ...)
"""

from .exceptions import AuthError, InvalidTokenError
from .models import Identity
from .providers import GoogleProvider, IdentityProvider, MockProvider
from .service import AuthService

__all__ = [
    "AuthService",
    "IdentityProvider",
    "GoogleProvider",
    "MockProvider",
    "Identity",
    "AuthError",
    "InvalidTokenError",
]

__version__ = "0.1.0"
