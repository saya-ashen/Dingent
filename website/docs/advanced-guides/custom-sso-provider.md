---
sidebar_position: 3
---

# Custom SSO Provider

Dingent supports custom single sign-on integrations through a small Python provider interface. This lets public Dingent keep only generic SSO plumbing while private deployments supply organization-specific protocol details in a separate package.

## Public Dingent Responsibilities

The public Dingent codebase owns the stable extension points:

- `SSOProvider`: builds the external login redirect URL and authenticates the callback.
- `SSOProfile`: normalizes the external identity into Dingent fields.
- `/api/v1/auth/sso/login`: redirects users to the configured provider.
- `/api/v1/auth/sso/callback`: receives the provider callback, creates or links a Dingent user, and issues Dingent's access token.
- `SSO_PROVIDER_CLASS`: imports a provider class from an installed Python package.

Public Dingent should not contain private SSO server URLs, private attribute names, organization-specific XML samples, or deployment secrets.

## Provider Contract

A provider class must expose a `name` attribute and implement these methods:

```python
from __future__ import annotations

from fastapi import Request

from dingent.server.auth.sso import SSOProfile


class ExampleSSOProvider:
    name = "example"

    def build_login_redirect_url(self, *, request: Request, next_url: str | None = None) -> str:
        """Return the external identity provider login URL."""
        raise NotImplementedError

    async def authenticate_callback(self, *, request: Request) -> SSOProfile:
        """Validate the provider callback and return a normalized identity."""
        raise NotImplementedError
```

`authenticate_callback()` should return an `SSOProfile`:

```python
SSOProfile(
    provider="example",
    subject="stable-provider-user-id",
    email="user@example.com",
    username="user",
    display_name="Example User",
    attributes={"source": "example"},
)
```

Field expectations:

- `provider`: stable provider name stored in Dingent's external identity table.
- `subject`: stable user identifier from the provider. Prefer an immutable provider ID over an email address.
- `email`: required when Dingent auto-creates users.
- `username`: optional display/login name. Dingent falls back when possible.
- `display_name`: optional full display name.
- `attributes`: optional raw provider attributes useful for auditing and troubleshooting.

## Private Package Pattern

Keep deployment-specific providers in a private package, for example:

```text
dingent-private-sso/
  pyproject.toml
  src/
    dingent_private_sso/
      __init__.py
      provider.py
  tests/
    test_provider.py
```

Install that package only in the private deployment image, then point Dingent at the provider class:

```env
SSO_ENABLED=true
SSO_PROVIDER_CLASS=dingent_private_sso.provider.PrivateSSOProvider
SSO_LABEL=Single Sign-On
SSO_AUTO_CREATE_USER=true
SSO_ALLOW_EMAIL_LINKING=false
SSO_CALLBACK_FRONTEND_URL=/auth/sso/callback
```

The private package can read its own environment variables, for example:

```env
PRIVATE_SSO_LOGIN_URL=https://idp.example.com/login
PRIVATE_SSO_VALIDATE_URL=https://idp.example.com/serviceValidate
PRIVATE_SSO_TIMEOUT_SECONDS=10
```

Do not commit those private values to the public Dingent repository.

## CAS Provider Sketch

For CAS-like providers, the private package normally does this:

1. Build a `service` URL from Dingent's `sso_callback` route.
2. Redirect to the external CAS login endpoint with that `service` URL.
3. Read `ticket` from the callback.
4. Validate the ticket against the CAS validation endpoint.
5. Parse the CAS XML response.
6. Map provider fields to `SSOProfile`.

Minimal shape:

```python
from __future__ import annotations

from urllib.parse import urlencode
from urllib.request import urlopen
from xml.etree import ElementTree

from fastapi import HTTPException, Request, status

from dingent.server.auth.sso import SSOProfile


class PrivateCASProvider:
    name = "private-cas"

    def build_login_redirect_url(self, *, request: Request, next_url: str | None = None) -> str:
        service_url = str(request.url_for("sso_callback"))
        if next_url:
            service_url = f"{service_url}?{urlencode({'next': next_url})}"
        return f"{self.login_url}?{urlencode({'service': service_url})}"

    async def authenticate_callback(self, *, request: Request) -> SSOProfile:
        ticket = request.query_params.get("ticket")
        if not ticket:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CAS callback requires ticket")

        service_url = str(request.url_for("sso_callback"))
        next_url = request.query_params.get("next")
        if next_url:
            service_url = f"{service_url}?{urlencode({'next': next_url})}"

        validate_url = f"{self.validate_url}?{urlencode({'service': service_url, 'ticket': ticket})}"
        with urlopen(validate_url, timeout=self.timeout_seconds) as response:
            payload = response.read()

        return self.parse_profile(payload)

    def parse_profile(self, payload: bytes) -> SSOProfile:
        root = ElementTree.fromstring(payload)
        namespace = {"cas": "http://www.yale.edu/tp/cas"}
        success = root.find("cas:authenticationSuccess", namespace)
        if success is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="CAS authentication failed")

        user_element = success.find("cas:user", namespace)
        if user_element is None or not user_element.text:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="CAS response does not include a user")

        subject = user_element.text.strip()
        return SSOProfile(provider=self.name, subject=subject, email=subject if "@" in subject else None, username=subject)
```

Use this only as a shape reference. Keep real field mapping, provider URLs, and organization-specific behavior in the private package.

## Deployment Checklist

- Install the private provider package in the Dingent runtime environment.
- Set `SSO_ENABLED=true`.
- Set `SSO_PROVIDER_CLASS` to the fully qualified class path.
- Register Dingent's backend callback URL with the identity provider: `/api/v1/auth/sso/callback`.
- Verify the provider returns a stable `subject` and an `email` when auto-creating users.
- Run the auth tests and one browser login flow before enabling SSO for users.
