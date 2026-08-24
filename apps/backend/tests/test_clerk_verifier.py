import uuid

import jwt as pyjwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from lessoncanvas.adapters import auth as auth_adapter


class FakeSigningKey:
    def __init__(self, public_pem):
        self.key = public_pem


class FakeJWKClient:
    def __init__(self, public_pem):
        self._public_pem = public_pem

    def get_signing_key_from_jwt(self, token):
        return FakeSigningKey(self._public_pem)


def _generate_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _make_verifier(public_pem, issuer="", audience=""):
    verifier = auth_adapter.ClerkJwksVerifier.__new__(auth_adapter.ClerkJwksVerifier)
    verifier._client = FakeJWKClient(public_pem)
    verifier._issuer = issuer
    verifier._audience = audience
    return verifier


def test_clerk_verifier_accepts_valid_rs256_session_token():
    private_pem, public_pem = _generate_keypair()
    clerk_user_id = f"user_{uuid.uuid4().hex[:20]}"
    token = pyjwt.encode({"sub": clerk_user_id}, private_pem, algorithm="RS256")

    verifier = _make_verifier(public_pem)
    subject = verifier.verify(token)

    assert subject is not None
    assert subject.clerk_user_id == clerk_user_id


def test_clerk_verifier_rejects_token_signed_with_wrong_key():
    private_pem, _ = _generate_keypair()
    _, other_public_pem = _generate_keypair()
    token = pyjwt.encode({"sub": "user_x"}, private_pem, algorithm="RS256")

    verifier = _make_verifier(other_public_pem)
    assert verifier.verify(token) is None


def test_clerk_verifier_rejects_missing_subject():
    private_pem, public_pem = _generate_keypair()
    token = pyjwt.encode({"st": "sign_in_token"}, private_pem, algorithm="RS256")

    verifier = _make_verifier(public_pem)
    assert verifier.verify(token) is None


def test_clerk_verifier_enforces_issuer():
    private_pem, public_pem = _generate_keypair()
    clerk_user_id = "user_issuer_check"
    token = pyjwt.encode(
        {"sub": clerk_user_id, "iss": "https://evil.example.com"}, private_pem, algorithm="RS256"
    )

    verifier = _make_verifier(public_pem, issuer="https://good.clerk.accounts.dev")
    assert verifier.verify(token) is None

    good_token = pyjwt.encode(
        {"sub": clerk_user_id, "iss": "https://good.clerk.accounts.dev"},
        private_pem,
        algorithm="RS256",
    )
    subject = verifier.verify(good_token)
    assert subject is not None
    assert subject.clerk_user_id == clerk_user_id
