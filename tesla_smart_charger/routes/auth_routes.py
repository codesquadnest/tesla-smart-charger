"""
OAuth 2.0 + PKCE authorization flow and basic-auth management.

Endpoints
---------
POST /auth/start        — Build the Tesla authorization URL and return it.
GET  /auth/callback     — Receive the code from Tesla, exchange for tokens.
GET  /auth/vehicles     — List Tesla vehicles accessible with in-flight tokens.
POST /api/v1/auth/setup — Configure (or disable) HTTP Basic Auth.
POST /api/v1/auth/verify — Verify a password against the stored hash.
"""

import base64
import hashlib
import ipaddress
import json
import os
import secrets
import threading
import time
import urllib.parse
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from tesla_smart_charger import constants, logger
from tesla_smart_charger.app_config import AppConfig

tsc_logger = logger.get_logger()

router = APIRouter(tags=["auth"])

_app_config: Optional[AppConfig] = None

# In-memory PKCE state store: state_token → {code_verifier, vehicle_id, expires_at}
# Guarded by _oauth_sessions_lock — concurrent /auth/start and /auth/callback
# requests run in FastAPI's threadpool and mutate this dict.
_oauth_sessions: Dict[str, Dict[str, Any]] = {}
_oauth_sessions_lock = threading.Lock()
SESSION_TTL = 600  # 10 minutes

# Completed OAuth results keyed by state so the frontend can retrieve them
# via a manual paste-URL fallback when postMessage / hash delivery fails.
_oauth_results: Dict[str, Dict[str, Any]] = {}
_oauth_results_lock = threading.Lock()
RESULT_TTL = 300  # 5 minutes

# Schemes allowed for the user-supplied tesla-http-proxy URL. Anything else
# (file:, gopher:, etc.) is rejected to limit SSRF surface.
_ALLOWED_PROXY_SCHEMES = ("http", "https")

# Known Tesla token issuers — used to validate the ``issuer`` param from the
# OAuth callback before constructing the token-exchange POST URL.  Anything
# outside this allowlist is rejected (SSRF + secret leakage guard).
_ALLOWED_TOKEN_ISSUERS = (
    "https://auth.tesla.com/oauth2/v3",
    "https://fleet-auth.prd.vn.cloud.tesla.com/oauth2/v3",
)


def init(app_config: AppConfig) -> None:
    global _app_config
    _app_config = app_config


def _validate_proxy_url(proxy_url: str) -> None:
    """
    Reject obviously unsafe proxy URLs before they are used to build outbound,
    token-bearing requests. Requires an http/https scheme and a host.

    Also rejects loopback / link-local IP addresses to limit SSRF surface,
    while allowing private (RFC1918) IPs since the proxy typically runs on
    the same LAN.
    """
    parsed = urllib.parse.urlparse(proxy_url)
    if parsed.scheme not in _ALLOWED_PROXY_SCHEMES or not parsed.hostname:
        raise HTTPException(
            status_code=400,
            detail="proxy_url must be an http(s) URL with a host.",
        )
    # Reject loopback and link-local IPs
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_loopback or ip.is_link_local:
            raise HTTPException(
                status_code=400,
                detail=f"proxy_url host {parsed.hostname} is not allowed.",
            )
    except ValueError:
        pass  # hostname, not an IP — can't validate further without DNS


def _callback_html(payload: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> str:
    """
    Return an HTML page that posts an OAuth result to the opener window via
    ``window.postMessage`` and immediately closes itself.

    This page is loaded inside the Tesla OAuth popup that the onboarding wizard
    opens.  After the server completes the token exchange it embeds the result
    in the page; the page then relays it to the wizard and closes.
    """
    if error:
        msg_obj = {"type": "tesla-auth-callback", "error": error}
    else:
        msg_obj = {**(payload or {}), "type": "tesla-auth-callback"}
    # Escape "</" so a value containing "</script>" (e.g. a vehicle name) can't
    # break out of the inline <script> block.
    msg = json.dumps(msg_obj).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tesla Authorization</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box}}
    body{{margin:0;font-family:system-ui,sans-serif;background:#f8fafc;
         display:flex;align-items:center;justify-content:center;min-height:100vh}}
    .card{{background:#fff;border-radius:12px;padding:2.5rem 2rem;text-align:center;
           box-shadow:0 4px 24px rgba(0,0,0,.08);max-width:340px;width:100%}}
    .spinner{{width:40px;height:40px;border:4px solid #e2e8f0;
              border-top-color:#3b82f6;border-radius:50%;
              animation:spin .8s linear infinite;margin:0 auto 1.25rem}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
    p{{color:#475569;margin:0;font-size:.95rem}}
    .err{{color:#dc2626}}
    .close-link{{display:none;margin-top:1rem;color:#3b82f6;cursor:pointer;
                 text-decoration:underline;font-size:.85rem}}
  </style>
</head>
<body>
  <div class="card">
    <div class="spinner"></div>
    <p id="msg">Completing authorization&hellip;</p>
    <p id="closeLink" class="close-link">Close this window</p>
  </div>
  <script>
    (function() {{
      var msg = {msg};
      try {{
        if (window.opener) {{
          window.opener.postMessage(msg, '*');
          // Also write tokens to the opener's URL hash as a fallback for
          // browsers / reverse-proxy setups that block postMessage delivery.
          try {{
            window.opener.location.hash =
              '#tsc-oauth=' + encodeURIComponent(JSON.stringify(msg));
          }} catch(e) {{ /* cross-origin hash not allowed — ignore */ }}
          document.getElementById('msg').textContent = 'Done! Closing\u2026';
          setTimeout(function() {{ window.close(); }}, 400);
          // If window.close() is blocked (common in modern browsers), show
          // a link so the user can close the popup manually after 3 seconds.
          setTimeout(function() {{
            if (!window.closed) {{
              document.getElementById('closeLink').style.display = 'block';
            }}
          }}, 3000);
        }} else {{
          document.getElementById('msg').className = 'err';
          document.getElementById('msg').textContent =
            'Could not communicate with the opener window. Please close this tab and try again.';
        }}
      }} catch(e) {{
        document.getElementById('msg').className = 'err';
        document.getElementById('msg').textContent = 'Error: ' + e.message;
      }}
    }})();
    document.getElementById('closeLink').addEventListener('click', function() {{
      window.close();
    }});
  </script>
</body>
</html>"""


# ─── PKCE helpers ──────────────────────────────────────────────────────────────

def _generate_code_verifier() -> str:
    return base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=").decode()


def _generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _clean_expired_sessions() -> None:
    now = time.time()
    with _oauth_sessions_lock:
        expired = [k for k, v in _oauth_sessions.items() if v["expires_at"] < now]
        for k in expired:
            del _oauth_sessions[k]


# ─── OAuth flow ────────────────────────────────────────────────────────────────

class AuthStartBody(BaseModel):
    """Body for /auth/start — credentials sent in POST body to avoid leaking
    the client_secret into server access logs, browser history, or proxies."""

    client_id: str
    client_secret: str = ""
    redirect_uri: str
    proxy_url: str
    region: str = "eu"


@router.post("/auth/start")
def auth_start(body: AuthStartBody) -> JSONResponse:
    """
    Build the Tesla OAuth 2.0 authorization URL (PKCE).

    The caller should redirect the user's browser to the returned ``auth_url``.
    """
    _clean_expired_sessions()
    _validate_proxy_url(body.proxy_url)

    state = secrets.token_urlsafe(32)
    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)

    with _oauth_sessions_lock:
        _oauth_sessions[state] = {
            "code_verifier": code_verifier,
            "client_id": body.client_id,
            "client_secret": body.client_secret,
            "redirect_uri": body.redirect_uri,
            "proxy_url": body.proxy_url,
            "region": body.region,
            "expires_at": time.time() + SESSION_TTL,
        }

    params = {
        "client_id": body.client_id,
        "redirect_uri": body.redirect_uri,
        "response_type": "code",
        "scope": constants.TESLA_OAUTH_SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{constants.TESLA_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return JSONResponse({"auth_url": auth_url, "state": state}, status_code=200)


def _perform_token_exchange(code: str, state: str, issuer: Optional[str] = None) -> Dict[str, Any]:
    """
    Look up the PKCE session, exchange the authorization code for tokens,
    and return the result payload dict.

    The ``issuer`` is taken from the callback URL's ``issuer`` query param
    (e.g. ``https://auth.tesla.com/oauth2/v3``).  The token endpoint is
    derived as ``{issuer}/token``.  If omitted, the legacy fleet-auth URL
    is used as a fallback.

    Raises ``HTTPException`` on error so callers (both the HTML callback and
    the JSON exchange endpoint) can handle failures uniformly.
    """
    with _oauth_sessions_lock:
        session = _oauth_sessions.pop(state, None)
    if session is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")
    if time.time() > session["expires_at"]:
        raise HTTPException(status_code=400, detail="OAuth session expired.")

    # Token endpoint — prefer the issuer from the callback URL, fall back to
    # the legacy fleet-auth URL.  Validate against an allowlist to prevent
    # SSRF and secret leakage to arbitrary endpoints.
    if issuer:
        validated_issuer = issuer.rstrip("/")
        if validated_issuer not in _ALLOWED_TOKEN_ISSUERS:
            raise HTTPException(status_code=400, detail="Invalid token issuer.")
        token_url = f"{validated_issuer}/token"
    else:
        token_url = constants.TESLA_API_TOKEN_URL

    token_data = {
        "grant_type": "authorization_code",
        "client_id": session["client_id"],
        "code": code,
        "redirect_uri": session["redirect_uri"],
        "code_verifier": session["code_verifier"],
    }
    if session.get("client_secret"):
        token_data["client_secret"] = session["client_secret"]
    # The audience parameter is required by the fleet-auth endpoint and
    # harmless for the auth.tesla.com endpoint.
    token_data["audience"] = constants.TESLA_FLEET_API_URLS.get(
        session["region"], constants.TESLA_AUDIENCE
    )
    try:
        r = requests.post(
            token_url,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20,
        )
        r.raise_for_status()
        tokens = r.json()
    except requests.RequestException as exc:
        tsc_logger.error("Token exchange failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Token exchange failed: {exc}") from exc

    access = tokens.get("access_token", "")
    refresh = tokens.get("refresh_token", "")

    if not access or not refresh:
        raise HTTPException(status_code=502, detail="Missing tokens in Tesla response.")

    vehicles_list: list = []
    try:
        from tesla_smart_charger.models import VehicleConfig
        from tesla_smart_charger.tesla_api import TeslaAPI

        tmp_vehicle = VehicleConfig(
            teslaAccessToken=access,
            teslaRefreshToken=refresh,
            teslaClientId=session["client_id"],
            teslaHttpProxy=session["proxy_url"],
            region=session["region"],
        )
        api = TeslaAPI(tmp_vehicle)
        vehicles_list = api.get_vehicles()
    except Exception as exc:
        tsc_logger.warning("Could not list vehicles after OAuth: %s", exc)

    payload: Dict[str, Any] = {
        "access_token": access,
        "refresh_token": refresh,
        "client_id": session["client_id"],
        "proxy_url": session["proxy_url"],
        "region": session["region"],
        "vehicles": vehicles_list,
    }

    with _oauth_results_lock:
        _oauth_results[state] = {
            "payload": payload,
            "expires_at": time.time() + RESULT_TTL,
        }

    return payload


def _handle_auth_callback(code: str, state: str, issuer: Optional[str] = None) -> HTMLResponse:
    """Shared OAuth callback logic — called by both /auth/callback and
    user-configured redirect URIs (e.g. /done.html)."""
    try:
        payload = _perform_token_exchange(code, state, issuer=issuer)
    except HTTPException as exc:
        return HTMLResponse(_callback_html(error=exc.detail))
    except Exception as exc:
        return HTMLResponse(_callback_html(error=str(exc)))
    return HTMLResponse(_callback_html(payload=payload))


@router.get("/auth/callback")
def auth_callback(
    code: str = Query(...),
    state: str = Query(...),
    issuer: Optional[str] = Query(None),
) -> HTMLResponse:
    """
    OAuth callback — exchanges the authorization code for access/refresh tokens.

    Tesla redirects the user's browser here after they approve access.  This
    endpoint performs the server-side token exchange and then returns a tiny
    HTML page that posts the result to the opener window (the onboarding
    wizard) via ``window.postMessage`` and closes itself.
    """
    return _handle_auth_callback(code, state, issuer=issuer)


# Alias for users whose Tesla developer app is configured with a custom
# redirect URI (e.g. https://tesla.example.com/done.html) instead of the
# default /auth/callback path.  Because the auth router is registered
# before the SPA catch-all in __main__.py this route takes precedence.
@router.get("/done.html")
def auth_callback_done(
    code: str = Query(...),
    state: str = Query(...),
    issuer: Optional[str] = Query(None),
) -> HTMLResponse:
    return _handle_auth_callback(code, state, issuer=issuer)


@router.get("/auth/result/{state}")
def get_auth_result(state: str) -> JSONResponse:
    """
    Retrieve a completed OAuth result by state token.

    This is the manual fallback: when the popup's postMessage / hash delivery
    fails, the user can paste the callback URL into the main window; the
    frontend extracts the ``state`` and calls this endpoint to retrieve the
    tokens that were stored after the successful token exchange.
    """
    with _oauth_results_lock:
        result = _oauth_results.pop(state, None)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found or expired.")
    if time.time() > result["expires_at"]:
        raise HTTPException(status_code=404, detail="Result expired.")
    return JSONResponse(result["payload"])


class OAuthExchangeBody(BaseModel):
    code: str
    state: str
    issuer: Optional[str] = None


class OAuthVehiclesBody(BaseModel):
    access_token: str
    proxy_url: str
    region: str = "eu"


@router.post("/auth/exchange")
def exchange_auth_code(body: OAuthExchangeBody) -> JSONResponse:
    """
    Manually exchange an authorization code for tokens using the pasted
    callback URL from the popup.

    This is the manual fallback for when the user's reverse proxy serves a
    static file at the redirect URI path (e.g. ``/done.html``) instead of
    forwarding the request to the backend.  The user copies the callback URL
    from the popup's address bar and pastes it into the main window; the
    frontend extracts ``code`` and ``state`` and calls this endpoint.
    """
    try:
        payload = _perform_token_exchange(body.code, body.state, issuer=body.issuer)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return JSONResponse(payload)


@router.post("/auth/vehicles")
def list_oauth_vehicles(body: OAuthVehiclesBody) -> JSONResponse:
    """
    Return the list of Tesla vehicles accessible with the provided token.
    Used during onboarding to let the user pick vehicles to manage.

    Credentials are sent in the request body (never the query string) to avoid
    leaking the access token into access logs / proxy caches.
    """
    from tesla_smart_charger.models import VehicleConfig
    from tesla_smart_charger.tesla_api import TeslaAPI

    _validate_proxy_url(body.proxy_url)
    tmp_vehicle = VehicleConfig(
        teslaAccessToken=body.access_token,
        teslaHttpProxy=body.proxy_url,
        region=body.region,
    )
    try:
        api = TeslaAPI(tmp_vehicle)
        vehicles = api.get_vehicles()
        return JSONResponse({"vehicles": vehicles}, status_code=200)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ─── Basic Auth management ─────────────────────────────────────────────────────

class AuthSetupBody(BaseModel):
    enabled: bool
    username: Optional[str] = None
    password: Optional[str] = None


class AuthVerifyBody(BaseModel):
    username: str
    password: str


def _hash_password(password: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        # Fallback: SHA-256 (less secure, but avoids hard dependency)
        return hashlib.sha256(password.encode()).hexdigest()


def _check_password(password: str, hashed: str) -> bool:
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ImportError:
        return hashlib.sha256(password.encode()).hexdigest() == hashed


@router.post("/api/v1/auth/setup")
def setup_auth(body: AuthSetupBody) -> JSONResponse:
    """Enable or disable HTTP Basic Auth and optionally set credentials."""
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")

    updates: Dict[str, Any] = {"auth": {"enabled": body.enabled}}

    if body.enabled:
        if not body.username or not body.password:
            raise HTTPException(
                status_code=400,
                detail="username and password are required when enabling auth.",
            )
        updates["auth"]["username"] = body.username
        updates["auth"]["passwordHash"] = _hash_password(body.password)
    else:
        updates["auth"]["username"] = ""
        updates["auth"]["passwordHash"] = ""

    _app_config.update_system(updates)
    return JSONResponse({"message": "Auth configuration updated."}, status_code=200)


@router.post("/api/v1/auth/verify")
def verify_auth(body: AuthVerifyBody) -> JSONResponse:
    """Verify a username/password against the stored hash. Returns 200 or 401."""
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")
    auth = _app_config.system.auth
    if not auth.enabled:
        return JSONResponse({"valid": True}, status_code=200)
    valid = (
        body.username == auth.username
        and bool(auth.passwordHash)
        and _check_password(body.password, auth.passwordHash)
    )
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    return JSONResponse({"valid": True}, status_code=200)
