"""Password hashing (Passlib/bcrypt) and JWT issue/verify (python-jose)."""

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.errors import TokenError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _encode(claims: dict, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {**claims, "iat": now, "exp": now + expires_delta, "jti": str(uuid.uuid4())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(*, user_id: str, tenant_id: str, role: str) -> str:
    return _encode(
        {"sub": user_id, "tenant_id": tenant_id, "role": role, "type": TOKEN_TYPE_ACCESS},
        timedelta(minutes=settings.access_token_minutes),
    )


def create_refresh_token(*, user_id: str, tenant_id: str, token_version: int) -> str:
    return _encode(
        {"sub": user_id, "tenant_id": tenant_id, "tv": token_version, "type": TOKEN_TYPE_REFRESH},
        timedelta(days=settings.refresh_token_days),
    )


def decode_token(token: str, *, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:  # expired or malformed
        raise TokenError("Token is invalid or expired.") from exc
    if payload.get("type") != expected_type:
        raise TokenError("Wrong token type.")
    return payload
