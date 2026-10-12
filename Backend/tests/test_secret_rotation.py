"""L5.4 : rotation du secret JWT sans déconnecter les utilisateurs."""

from jose import jwt

from tests.api_stub import install

install()

from api.services import auth_service  # noqa: E402
from config.settings import get_settings  # noqa: E402

OLD_KEY = "old-secret-" + "o" * 40


def _token_signed_with(key: str, token_type="access", user_id="u1"):
    return jwt.encode(
        {"sub": user_id, "type": token_type, "exp": 9999999999}, key, algorithm="HS256"
    )


def test_tokens_from_the_previous_key_are_accepted_only_while_configured(monkeypatch):
    old = _token_signed_with(OLD_KEY)
    assert auth_service.decode_token(old, "access") is None  # clé inconnue

    monkeypatch.setattr(get_settings(), "JWT_SECRET_KEY_PREVIOUS", f" {OLD_KEY} , autre-cle")
    assert auth_service.decode_token(old, "access")["sub"] == "u1"
    assert auth_service.decode_token(old, "refresh") is None  # le type reste contrôlé

    monkeypatch.setattr(get_settings(), "JWT_SECRET_KEY_PREVIOUS", "")
    assert auth_service.decode_token(old, "access") is None  # rotation terminée


def test_new_tokens_are_always_signed_with_the_current_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "JWT_SECRET_KEY_PREVIOUS", OLD_KEY)
    token = auth_service.create_access_token("u9")
    assert jwt.decode(token, auth_service.SECRET_KEY, algorithms=["HS256"])["sub"] == "u9"
    try:
        jwt.decode(token, OLD_KEY, algorithms=["HS256"])
    except Exception:
        pass
    else:  # pragma: no cover
        raise AssertionError("un jeton neuf ne doit pas être signé avec l'ancienne clé")


def test_garbage_and_expired_tokens_are_rejected(monkeypatch):
    monkeypatch.setattr(get_settings(), "JWT_SECRET_KEY_PREVIOUS", OLD_KEY)
    assert auth_service.decode_token("pas-un-jwt", "access") is None
    expired = jwt.encode({"sub": "u", "type": "access", "exp": 1}, OLD_KEY, algorithm="HS256")
    assert auth_service.decode_token(expired, "access") is None
