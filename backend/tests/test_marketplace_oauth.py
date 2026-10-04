from app.services.marketplace_oauth import generate_pkce_pair
from app.services.marketplace_crypto import encrypt_secret, decrypt_secret

def test_pkce_pair_is_generated():
    verifier, challenge = generate_pkce_pair()
    assert len(verifier) >= 43
    assert len(challenge) >= 43
    assert verifier != challenge

def test_marketplace_secrets_roundtrip():
    encrypted = encrypt_secret("segredo-marketplace")
    assert encrypted != "segredo-marketplace"
    assert decrypt_secret(encrypted) == "segredo-marketplace"
