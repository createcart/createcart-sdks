# createcart-auth — Auth SDK

Pluggable **customer identity** for CreateCart storefronts. Providers verify a
login token and return an `Identity`. A **Google** provider ("Sign in with
Google") and a **Mock** provider (local dev / tests — no Google project) ship in
the box.

- **Language:** Python ≥ 3.10 · **Import:** `createcart_auth`
- Google ID tokens verified via Google's `tokeninfo` endpoint (urllib) — **no
  google-auth / JWT dependency**.

---

## How "Sign in with Google" works here

```
browser  Google Identity Services button → user picks account → ID token (JWT)
browser  POST /api/auth/google { id_token }
server   AuthService.verify(id_token)  → checks signature+expiry (Google) and
         audience+issuer (us)          → Identity { sub, email, name, picture }
```

The **audience check** (token was minted for *our* client id) is the
security-critical step and is unit-tested.

## What's inside

```
packages/auth/
├─ src/createcart_auth/
│  ├─ service.py        # AuthService.verify(token) -> Identity
│  ├─ models.py         # Identity(provider, subject, email, email_verified, name, picture)
│  ├─ exceptions.py     # AuthError, InvalidTokenError
│  └─ providers/
│     ├─ base.py        # IdentityProvider protocol
│     ├─ google.py      # GoogleProvider(client_id)
│     └─ mock.py        # MockProvider (make_token / verify_token)
└─ tests/test_auth.py   # 6 tests
```

## Usage

```python
from createcart_auth import AuthService, GoogleProvider, MockProvider

# production
auth = AuthService(GoogleProvider(client_id="123-abc.apps.googleusercontent.com"))
identity = auth.verify(id_token_from_browser)     # raises InvalidTokenError if bad
print(identity.email, identity.name, identity.subject)

# local / tests (no Google project)
auth = AuthService(MockProvider())
auth.verify("mock")                                # -> demo@example.com
```

`auth.public_config` returns the non-secret config the frontend needs
(`{provider, client_id}` for Google, `{provider}` for mock).

## Add a provider

```python
class AppleProvider:
    name = "apple"
    @property
    def public_config(self) -> dict: ...
    def verify_token(self, token) -> Identity: ...
```

## Test

```powershell
.\.venv\Scripts\pytest packages/auth -q
```
