"""Unit tests for password hashing and JWT issue/verify."""

import pytest

from app.core.errors import TokenError
from app.core.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("supersecret1")
    assert h != "supersecret1"
    assert verify_password("supersecret1", h) is True
    assert verify_password("wrong", h) is False


def test_access_token_decodes_with_claims():
    token = create_access_token(user_id="u1", tenant_id="t1", role="OWNER")
    payload = decode_token(token, expected_type=TOKEN_TYPE_ACCESS)
    assert payload["sub"] == "u1"
    assert payload["tenant_id"] == "t1"
    assert payload["role"] == "OWNER"
    assert payload["type"] == TOKEN_TYPE_ACCESS
    assert "jti" in payload and "exp" in payload


def test_refresh_token_carries_token_version():
    token = create_refresh_token(user_id="u1", tenant_id="t1", token_version=3)
    payload = decode_token(token, expected_type=TOKEN_TYPE_REFRESH)
    assert payload["tv"] == 3


def test_wrong_token_type_rejected():
    access = create_access_token(user_id="u1", tenant_id="t1", role="OWNER")
    with pytest.raises(TokenError):
        decode_token(access, expected_type=TOKEN_TYPE_REFRESH)


def test_tampered_token_rejected():
    token = create_access_token(user_id="u1", tenant_id="t1", role="OWNER")
    tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    with pytest.raises(TokenError):
        decode_token(tampered, expected_type=TOKEN_TYPE_ACCESS)
