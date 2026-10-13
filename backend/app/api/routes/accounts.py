from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from app.api.booking_schemas import AuthResponse, LoginRequest, SignupRequest, UserOut
from app.auth import users
from app.auth.deps import current_user
from app.auth.security import AuthConfigError, create_token, ensure_configured, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Accounts"])


def _check_config() -> None:
    try:
        ensure_configured()
    except AuthConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _auth_response(user: dict) -> dict:
    return {"token": create_token(user["_id"], user["role"]), "user": users.public(user)}


@lru_cache
def _dummy_hash() -> str:
    """Used when the email is unknown, so a login takes the same time either way."""
    return hash_password("not-a-real-password")


@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(body: SignupRequest) -> dict:
    _check_config()
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="Please enter your name.")
    try:
        user = users.create_user(body.name, body.email, hash_password(body.password))
    except users.EmailTaken:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest) -> dict:
    _check_config()
    user = users.find_by_email(body.email)
    password_ok = verify_password(body.password, user["password_hash"] if user else _dummy_hash())
    if not user or not password_ok:
        # one message for both cases, so nobody can find out which emails have accounts
        raise HTTPException(status_code=401, detail="Wrong email or password.")
    return _auth_response(user)


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(current_user)) -> dict:
    return users.public(user)