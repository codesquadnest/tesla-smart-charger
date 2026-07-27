"""
Password hashing and the HTTP Basic Auth guard for vehicle command endpoints.

Commands with physical-world effects (waking a car, changing its charge limit)
are gated behind ``require_auth``.  The guard **fails closed**: when Basic Auth
has not been configured the commands are refused outright rather than left open,
so an unprotected deployment cannot be driven by anyone who can reach the port.
"""

import secrets
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from tesla_smart_charger import logger
from tesla_smart_charger.app_config import AppConfig

tsc_logger = logger.get_logger()

# auto_error=False so a missing header reaches us as None — we return our own
# 401 with a WWW-Authenticate challenge, and a 403 when auth isn't configured.
_basic = HTTPBasic(auto_error=False)

_UNAUTHENTICATED_HEADERS = {"WWW-Authenticate": 'Basic realm="tesla-smart-charger"'}

AUTH_DISABLED_DETAIL = (
    "Vehicle commands are disabled because HTTP Basic Auth is not enabled. "
    "Enable it under Settings → Security to use them."
)

_app_config: AppConfig | None = None


def init(app_config: AppConfig) -> None:
    """Inject the shared AppConfig instance used by the auth guard."""
    global _app_config
    _app_config = app_config


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (a required dependency — see pyproject.toml)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    """Verify a password against a stored hash produced by `hash_password`."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def auth_configured() -> bool:
    """Whether Basic Auth is enabled *and* has a usable username + password hash."""
    if _app_config is None:
        return False
    auth = _app_config.system.auth
    return bool(auth.enabled and auth.username and auth.passwordHash)


def require_auth(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic)],
) -> str:
    """
    FastAPI dependency guarding the vehicle command endpoints.

    Raises 503 before the app is wired, 403 when Basic Auth has not been
    configured (fail closed — see the module docstring), and 401 when
    credentials are absent or wrong.  Returns the authenticated username.
    """
    if _app_config is None:
        raise HTTPException(status_code=503, detail="Not initialised")

    if not auth_configured():
        raise HTTPException(status_code=403, detail=AUTH_DISABLED_DETAIL)

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers=_UNAUTHENTICATED_HEADERS,
        )

    auth = _app_config.system.auth
    # compare_digest on the username too: a plain == leaks its length/prefix
    # through timing, and the password check below is only reached on a match.
    username_ok = secrets.compare_digest(credentials.username, auth.username)
    password_ok = check_password(credentials.password, auth.passwordHash)
    if not (username_ok and password_ok):
        tsc_logger.warning(
            "Rejected command request for user %r: invalid credentials.",
            credentials.username,
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials.",
            headers=_UNAUTHENTICATED_HEADERS,
        )

    return credentials.username
