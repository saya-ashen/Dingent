---
sidebar_position: 4
---

# SSO Deployment Guide

This guide covers end-to-end SSO integration for **private Dingent deployments**. It assumes you have:

- A running Dingent instance (backend + frontend)
- Access to a CAS 2.0 identity provider
- A private copy of the internal SSO provider (`sso_internal.py`)

For the SSO extension framework and provider contract, see [Custom SSO Provider](./custom-sso-provider.md).

## Architecture

```
Browser                    Dingent                     CAS IdP
  │                          │                           │
  ├─ click "SSO" ──────────►│                           │
  │  GET /auth/sso/login     │                           │
  │                          ├─ 307 redirect ───────────►│ /login?service=<callback>
  │                          │                           │
  │  ◄────── CAS login page ─────────────────────────────┤
  │                          │                           │
  │  ─── authenticate ──────────────────────────────────►│
  │                          │                           │
  │  ◄── redirect ───────────────────────────────────────┤
  │  GET /auth/sso/callback?ticket=ST-xxx                │
  │                          │                           │
  │                          ├─ validate ticket ────────►│ /serviceValidate
  │                          │◄── CAS XML ───────────────│
  │                          │                           │
  │                          ├─ create/link user         │
  │                          ├─ issue Dingent JWT        │
  │                          │                           │
  │  ◄── 307 redirect ───────┤                           │
  │  /auth/sso/callback?token=<jwt>&next=/               │
  │                          │                           │
  │  Frontend callback:      │                           │
  │    reads token            │                           │
  │    GET /auth/me ─────────►│                           │
  │    ◄── user profile ──────│                           │
  │    setAuth(token, user)   │                           │
  │    router.replace(next)   │                           │
```

## Integration Approaches

### A: Private Fork (Recommended)

Place the internal SSO provider directly in the Dingent source tree. The provider is a single file with CAS URLs hardcoded — no extra packages, no Dockerfile changes.

**Provider location:**

```
src/dingent/server/auth/sso_internal.py
```

**Configuration** (add to `.env`):

```env
SSO_ENABLED=true
SSO_PROVIDER_CLASS=dingent.server.auth.sso_internal.InternalCASProvider
SSO_LABEL=Single Sign-On
SSO_AUTO_CREATE_USER=true
```

All CAS server URLs and attribute mappings are hardcoded in the provider file. No additional `INTERNAL_SSO_*` variables are needed.

The public Dingent repository stays clean — the private fork only differs by one file.

### B: Separate Private Package

Keep the provider in a standalone package outside the Dingent repository.

**Package structure:**

```text
dingent-internal-sso/
  pyproject.toml
  src/dingent_internal_sso/
    __init__.py
    provider.py
    py.typed
  tests/
    test_provider.py
```

**Install:**

```bash
uv pip install /path/to/dingent-internal-sso
```

**Configuration:**

```env
SSO_ENABLED=true
SSO_PROVIDER_CLASS=dingent_internal_sso.provider.InternalCASProvider
SSO_LABEL=Single Sign-On
SSO_AUTO_CREATE_USER=true
```

For Docker, add to `Dockerfile.backend`:

```dockerfile
COPY dingent-internal-sso/ /tmp/dingent-internal-sso/
RUN uv pip install /tmp/dingent-internal-sso/ && rm -rf /tmp/dingent-internal-sso/
```

## Configuration Reference

### Dingent Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SSO_ENABLED` | `false` | Master switch. When `false`, SSO endpoints return 404. |
| `SSO_PROVIDER_CLASS` | (none) | Fully qualified Python class path. Takes priority over `SSO_PROVIDER`. |
| `SSO_PROVIDER` | `mock` | Built-in provider: `mock` (dev) or `cas` (basic CAS). Ignored when `SSO_PROVIDER_CLASS` is set. |
| `SSO_LABEL` | `SSO` | Text displayed on the SSO login button. |
| `SSO_AUTO_CREATE_USER` | `true` | Auto-create a Dingent user for new SSO identities. |
| `SSO_ALLOW_EMAIL_LINKING` | `false` | Link SSO identity to an existing user by matching email. Disabled by default for security. |
| `SSO_CALLBACK_FRONTEND_URL` | `/auth/sso/callback` | URL the backend redirects to after issuing a JWT. |

### `SSO_CALLBACK_FRONTEND_URL` by Environment

This is the most environment-sensitive setting:

| Environment | Value | Why |
|-------------|-------|-----|
| **Local dev** | `http://localhost:3000/dingent/web/auth/sso/callback` | Frontend runs on port 3000 with basePath `/dingent/web` |
| **Docker (compose)** | `http://localhost:3000/dingent/web/auth/sso/callback` | Frontend container serves on 3000 |
| **Docker (with nginx)** | `/auth/sso/callback` | Reverse proxy handles routing; relative URL works |
| **Production (same origin)** | `/auth/sso/callback` | Nginx routes `/auth/*` to frontend, `/api/*` to backend |

### .env Location

The `.env` file location depends on how Dingent is launched:

| Runtime | Location |
|---------|----------|
| `docker compose` | `./data/config/.env` (host side, mounted as `/app/data/config/.env`) |
| `dingent run` (no `--data-dir`) | `~/.config/dingent/.env` (Linux) |
| `dingent run --data-dir /path` | `/path/config/.env` |

## CAS Registration

Register the Dingent callback URL with your CAS server:

```
https://your-dingent-domain.example.com/api/v1/auth/sso/callback
```

For local development with `localhost`, ensure the CAS server is configured to accept `http://localhost` as a valid service URL.

## Local Development Setup

### 1. Start the backend

```bash
cd /path/to/dingent
uv run uvicorn dingent.server.main:app --host 0.0.0.0 --port 8000
```

### 2. Start the frontend

```bash
cd /path/to/dingent/ui
bun run dev
```

The frontend starts on `http://localhost:3000` with basePath `/dingent/web`. API calls are proxied to the backend via Next.js rewrites.

### 3. Verify SSO configuration

```bash
curl http://localhost:8000/api/v1/auth/config
```

Expected response:

```json
{
  "password_login_enabled": true,
  "sso_enabled": true,
  "sso_label": "Single Sign-On",
  "sso_login_url": "/auth/sso/login"
}
```

If `sso_enabled` is `false`, check:
- `.env` file is in the correct location
- `SSO_ENABLED=true` is present
- The provider class is importable

### 4. CORS Requirements

When the frontend runs on a different port than the backend, CORS must allow cross-origin requests. The default CORS configuration in `app.py` includes:

```python
"http://localhost:3001",  # Add http://localhost:3000 if your frontend uses it
"http://localhost:8000",
"http://localhost:5173",
```

In Docker deployments, API requests go through Next.js server-side rewrites and do not trigger CORS. The CORS list only matters when the browser makes direct cross-origin API calls.

## Troubleshooting

### SSO button does not appear on login page

The frontend calls `GET /auth/config` to determine whether to show the SSO button. Check:

1. `SSO_ENABLED=true` in the `.env` file at the correct location
2. The backend log shows no import errors for `SSO_PROVIDER_CLASS`
3. `curl http://localhost:8000/api/v1/auth/config` returns `sso_enabled: true`

### "SSO_PROVIDER_CLASS must be a fully qualified class path"

The value must include both module and class name separated by `.`:

```
✓ SSO_PROVIDER_CLASS=dingent.server.auth.sso_internal.InternalCASProvider
✗ SSO_PROVIDER_CLASS=dingent.server.auth.sso_internal
```

### Redirect loops or "Not Found" after SSO login

- **Local dev**: `SSO_CALLBACK_FRONTEND_URL` must be an **absolute** URL including port and basePath, e.g. `http://localhost:3000/dingent/web/auth/sso/callback`.
- **Docker (no reverse proxy)**: Same as above — absolute URL with the frontend container port.
- **Docker (with nginx)**: Use relative path `/auth/sso/callback`.

### "CAS authentication failed" (401)

The CAS server rejected the ticket. Verify:

1. `INTERNAL_SSO_VALIDATE_URL` points to the correct `serviceValidate` endpoint.
2. The `service` parameter sent to CAS matches the Dingent callback URL registered with CAS.
3. The ticket has not expired and has not been used before.

### "CAS profile does not include an email address" (400)

The CAS response must contain an email. Check:

1. The CAS XML includes an email attribute matching `INTERNAL_SSO_EMAIL_ATTRIBUTE` (default: `email`).
2. OR the `<cas:user>` value contains an `@` sign (fallback).

### "CAS server unreachable" (502)

The backend cannot reach the CAS validation endpoint.

1. Check network connectivity from the Dingent container/host to the CAS server.
2. Verify `INTERNAL_SSO_VALIDATE_URL` is correct.
3. Check firewall rules and DNS resolution.

### ModuleNotFoundError: No module named 'dingent.server.auth.sso_internal'

The provider class path cannot be imported. Verify:

1. The file exists at `src/dingent/server/auth/sso_internal.py`.
2. For separate packages, the package is installed in the runtime environment.
3. `PYTHONPATH` includes the source directory (set in Dockerfile and by `dingent run`).

### User returns to login page after SSO callback

The frontend callback page redirects to the URL in the `next` query parameter. The login page sends `next=/` (home page). If you see `/auth/login` as the `next` value, the login page implementation may need updating — the `handleSsoLogin()` function should set `next` to `"/"`, not the current page path.
