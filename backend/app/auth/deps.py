"""FastAPI dependency that turns 'Authorization: Bearer <token>' into the logged-in user."""
from fastapi import Header, HTTPException

from app.auth import users
from app.auth.security import AuthConfigError, decode_token


def current_user(authorization: str | None = Header(default=None)) -> dict:
    unauthorized = HTTPException(
        status_code=401, detail="Please log in.", headers={"WWW-Authenticate": "Bearer"}
    )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise unauthorized

    try:
        claims = decode_token(authorization[7:].strip())
    except AuthConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not claims:
        raise unauthorized

    user = users.find_by_id(claims.get("sub", ""))
    if not user:
        raise unauthorized
    return user