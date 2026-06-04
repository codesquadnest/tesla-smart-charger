"""
OAuth 2.0 + PKCE authorization flow and basic-auth management.

Endpoints
---------
GET  /auth/start        — Build the Tesla authorization URL and return it.
GET  /auth/callback     — Receive the code from Tesla, exchange for tokens.
GET  /auth/vehicles     — List Tesla vehicles accessible with in-flight tokens.
POST /api/v1/auth/setup — Configure (or disable) HTTP Basic Auth.
POST /api/v1/auth/verify — Verify a password against the stored hash.
"""

import base64
import hashlib
import json
import os
import secrets
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
_oauth_sessions: Dict[str, Dict[str, Any]] = {}
SESSION_TTL = 600  # 10 minutes


def init(app_config: AppConfig) -> None:
    global _app_config
    _app_config = app_config


def _callback_html(payload: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> str:
    """
    Return an HTML page that posts an OAuth result to the opener window via
    ``window.postMessage`` and immediately closes itself.

    This page is loaded inside the Tesla OAuth popup that the onboarding wizard
    opens.  After the server completes the token exchange it embeds the result
    in the page; the page then relays it to the wizard and closes.
    """
    if error:
        msg = json.dumps({"type": "tesla-auth-callback", "error": error})
    else:
        msg = json.dumps({**(payload or {}), "type": "tesla-auth-callback"})

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
  </style>
</head>
<body>
  <div class="card">
    <div class="spinner"></div>
    <p id="msg">Completing authorization&hellip;</p>
  </div>
  <script>
    (function() {{
      var msg = {msg};
      try {{
        if (window.opener) {{
          window.opener.postMessage(msg, '*');
          document.getElementById('msg').textContent = 'Done! Closing\u2026';
          setTimeout(function() {{ window.close(); }}, 400);
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
    expired = [k for k, v in _oauth_sessions.items() if v["expires_at"] < now]
    for k in expired:
        del _oauth_sessions[k]


# ─── OAuth flow ────────────────────────────────────────────────────────────────

@router.get("/auth/start")
def auth_start(
    client_id: str = Query(..., description="Tesla developer app client_id"),
    redirect_uri: str = Query(..., description="Your registered callback URL, e.g. http://host:8000/auth/callback"),
    proxy_url: str = Query(..., description="URL of the local tesla-http-proxy"),
    region: str = Query("eu", description="Tesla region: eu | na | ap"),
) -> JSONResponse:
    """
    Build the Tesla OAuth 2.0 authorization URL (PKCE).

    The caller should redirect the user's browser to the returned ``auth_url``.
    """
    _clean_expired_sessions()

    state = secrets.token_urlsafe(32)
    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)

    _oauth_sessions[state] = {
        "code_verifier": code_verifier,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "proxy_url": proxy_url,
        "region": region,
        "expires_at": time.time() + SESSION_TTL,
    }

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": constants.TESLA_OAUTH_SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{constants.TESLA_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return JSONResponse({"auth_url": auth_url, "state": state}, status_code=200)


@router.get("/auth/callback")
def auth_callback(
    code: str = Query(...),
    state: str = Query(...),
) -> HTMLResponse:
    """
    OAuth callback — exchanges the authorization code for access/refresh tokens.

    Tesla redirects the user's browser here after they approve access.  This
    endpoint performs the server-side token exchange and then returns a tiny
    HTML page that posts the result to the opener window (the onboarding
    wizard) via ``window.postMessage`` and closes itself.
    """
    session = _oauth_sessions.pop(state, None)
    if session is None:
        return HTMLResponse(_callback_html(error="Invalid or expired OAuth state."))
    if time.time() > session["expires_at"]:
        return HTMLResponse(_callback_html(error="OAuth session expired."))

    # Exchange authorization code for tokens
    token_data = {
        "grant_type": "authorization_code",
        "client_id": session["client_id"],
        "code": code,
        "redirect_uri": session["redirect_uri"],
        "code_verifier": session["code_verifier"],
        "audience": constants.TESLA_FLEET_API_URLS.get(session["region"], constants.TESLA_AUDIENCE),
    }
    try:
        r = requests.post(
            constants.TESLA_API_TOKEN_URL,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20,
        )
        r.raise_for_status()
        tokens = r.json()
    except requests.RequestException as exc:
        tsc_logger.error("Token exchange failed: %s", exc)
        return HTMLResponse(_callback_html(error=f"Token exchange failed: {exc}"))

    access = tokens.get("access_token", "")
    refresh = tokens.get("refresh_token", "")

    if not access or not refresh:
        return HTMLResponse(_callback_html(error="Missing tokens in Tesla response."))

    # Optionally fetch vehicle list using the new token so the wizard can
    # pre-populate the vehicle picker without an extra round-trip.
    vehicles_list: list = []
    try:
        from tesla_smart_charger.models import VehicleConfig
        from tesla_smart_charger.tesla_api import TeslaAPI

        tmp_vehicle = VehicleConfig(
            teslaAccessToken=access,
            teslaRefreshToken=refresh,
            teslaClientId=session["client_id"],
            teslaHttpProxy=session["proxy_url"],
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
    return HTMLResponse(_callback_html(payload=payload))


@router.get("/auth/vehicles")
def list_oauth_vehicles(
    access_token: str = Query(...),
    proxy_url: str = Query(...),
) -> JSONResponse:
    """
    Return the list of Tesla vehicles accessible with the provided token.
    Used during onboarding to let the user pick vehicles to manage.
    """
    from tesla_smart_charger.models import VehicleConfig
    from tesla_smart_charger.tesla_api import TeslaAPI

    tmp_vehicle = VehicleConfig(
        teslaAccessToken=access_token,
        teslaHttpProxy=proxy_url,
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
def verify_auth(body: AuthVerifyBody, username: str = Query(...)) -> JSONResponse:
    """Verify a username/password against the stored hash. Returns 200 or 401."""
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")
    auth = _app_config.system.auth
    if not auth.enabled:
        return JSONResponse({"valid": True}, status_code=200)
    valid = (
        username == auth.username
        and bool(auth.passwordHash)
        and _check_password(body.password, auth.passwordHash)
    )
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    return JSONResponse({"valid": True}, status_code=200)
