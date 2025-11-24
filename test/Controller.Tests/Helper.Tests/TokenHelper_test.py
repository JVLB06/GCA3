import jwt
from datetime import timedelta

from src.Helper.TokenHelper import TokenHelper


def test_create_access_token_generates_valid_jwt():
    helper = TokenHelper()
    data = {"sub": "user@example.com"}

    token = helper.create_access_token(data)

    # Deve retornar uma string (JWT)
    assert isinstance(token, str)

    # O próprio helper deve conseguir validar o token
    payload = helper.verify_token(token)
    assert payload is not None
    assert payload["sub"] == "user@example.com"
    assert "exp" in payload  # expiração presente


def test_verify_token_returns_none_for_invalid_signature():
    helper = TokenHelper()
    wrong_secret = "wrong_secret_key"

    # Gera um token com outra secret pra forçar InvalidSignature
    token = jwt.encode({"sub": "user@example.com"}, wrong_secret, algorithm=helper.algorithm)

    payload = helper.verify_token(token)

    # Como a assinatura não bate com a secret interna, deve ser inválido
    assert payload is None


def test_verify_token_returns_none_for_expired_token():
    helper = TokenHelper()
    data = {"sub": "user@example.com"}

    # Token já expirado (exp no passado)
    token = helper.create_access_token(data, expires_delta=timedelta(seconds=-1))

    payload = helper.verify_token(token)

    # verify_token deve capturar ExpiredSignatureError e retornar None
    assert payload is None


def test_get_current_user_returns_sub_when_token_is_valid():
    helper = TokenHelper()

    token = helper.create_access_token({"sub": "user@example.com"})

    current_user = helper.get_current_user(token)

    assert current_user == "user@example.com"


def test_get_current_user_returns_none_when_token_is_invalid():
    helper = TokenHelper()

    # Token totalmente inválido
    current_user = helper.get_current_user("isso.nao.eh.um.jwt")

    assert current_user is None
