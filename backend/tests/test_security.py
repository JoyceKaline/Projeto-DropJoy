from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

def test_password_hash_roundtrip():
    hashed = hash_password("segredo-forte")
    assert hashed != "segredo-forte"
    assert verify_password("segredo-forte", hashed)
    assert not verify_password("senha-errada", hashed)

def test_access_token_contains_user_and_tenant():
    token = create_access_token(user_id=7, tenant_id=3, email="qa@example.com")
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["tenant_id"] == 3
    assert payload["email"] == "qa@example.com"
