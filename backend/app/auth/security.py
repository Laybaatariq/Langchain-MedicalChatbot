"""
Password hashing (scrypt, from the Python standard library) and login tokens (JWT).
"""
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

settings = get_settings()

# scrypt cost settings (about 16 MB of memory per hash)
_N, _R, _P = 2**14, 8, 1


class AuthConfigError(RuntimeError):
    """The server is missing a setting that logins need."""


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def hash_password(password: str) -> str:
    """Returns 'scrypt$N$r$p$salt$hash'. A fresh random salt is used every time."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32
        )
        return hmac.compare_digest(digest, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False


def ensure_configured() -> str:
    """Returns the JWT secret, or raises AuthConfigError with a clear message."""
    secret = settings.jwt_secret
    if len(secret) < 32:
        raise AuthConfigError(
            "JWT_SECRET is missing or too short. Add a random value of at least 32 characters "
            "to backend/.env (see the README for the command that creates one)."
        )
    return secret


def create_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(claims, ensure_configured(), algorithm="HS256")


def decode_token(token: str) -> dict | None:
    """The token's claims, or None if it is wrong, tampered with or expired."""
    secret = ensure_configured()
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None