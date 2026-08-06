"""Security helper tests."""

from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hash_and_verify():
    hashed = hash_password("Str0ng!Pass")
    assert hashed != "Str0ng!Pass"
    assert verify_password("Str0ng!Pass", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token("user-123", {"roles": ["user"]})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert payload["roles"] == ["user"]
