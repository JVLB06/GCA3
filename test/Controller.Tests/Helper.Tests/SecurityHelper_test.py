import pytest
from fastapi import HTTPException, Request
from starlette.responses import Response

from src.Helper.SecurityHelper import (
    authenticate_request,
    get_current_user_from_token,
)
from src.Model import TokenModel


# ===================== Fakes de TokenHelper =====================


class FakeTokenHelperValid:
    def __init__(self, *args, **kwargs):
        pass

    def get_current_user(self, token: str):
        # sempre considera token válido
        return "user@example.com"


class FakeTokenHelperInvalid:
    def __init__(self, *args, **kwargs):
        pass

    def get_current_user(self, token: str):
        # sempre considera token inválido
        return None


# ===================== Helper para criar Request =====================


def make_request(path: str, headers: dict | None = None) -> Request:
    """
    Cria um objeto Request manualmente, para testar o middleware
    sem precisar subir um FastAPI app inteiro.
    """
    raw_headers = []
    headers = headers or {}
    for k, v in headers.items():
        raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))

    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": raw_headers,
        "query_string": b"",
        "client": ("testclient", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
    }
    return Request(scope)


# ===================== TESTES DO MIDDLEWARE authenticate_request =====================


@pytest.mark.anyio
async def test_middleware_allows_public_route_without_token():
    # "/" está em PUBLIC_ROUTES, então não deve exigir token
    request = make_request("/")

    async def call_next(req: Request):
        # simula próxima camada retornando 200 OK
        return Response("public ok", status_code=200)

    response = await authenticate_request(request, call_next)

    assert response.status_code == 200
    assert response.body == b"public ok"


@pytest.mark.anyio
async def test_middleware_denies_private_route_without_token():
    # Rota não pública, sem Authorization -> 401 "Token missing or invalid"
    request = make_request("/private")

    async def call_next(req: Request):
        # não deveria nem chegar aqui
        raise AssertionError("call_next não deveria ser chamado")

    with pytest.raises(HTTPException) as exc:
        await authenticate_request(request, call_next)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token missing or invalid"


@pytest.mark.anyio
async def test_middleware_denies_private_route_with_invalid_token(monkeypatch):
    # Token presente, mas TokenHelper considera inválido -> 401 "Token expired or invalid"
    request = make_request(
        "/private",
        headers={"Authorization": "Bearer token-invalido"},
    )

    async def call_next(req: Request):
        raise AssertionError("call_next não deveria ser chamado")

    # Mocka TokenHelper dentro do módulo SecurityHelper
    monkeypatch.setattr(
        "src.Helper.SecurityHelper.TokenHelper",
        FakeTokenHelperInvalid,
    )

    with pytest.raises(HTTPException) as exc:
        await authenticate_request(request, call_next)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token expired or invalid"


@pytest.mark.anyio
async def test_middleware_allows_private_route_with_valid_token(monkeypatch):
    # Token presente e válido -> deve chamar call_next e setar request.state.user
    request = make_request(
        "/private",
        headers={"Authorization": "Bearer token-valido"},
    )

    called = {"value": False}
    captured_user = {"value": None}

    async def call_next(req: Request):
        called["value"] = True
        # user deve ter sido setado pelo middleware
        captured_user["value"] = getattr(req.state, "user", None)
        return Response("private ok", status_code=200)

    monkeypatch.setattr(
        "src.Helper.SecurityHelper.TokenHelper",
        FakeTokenHelperValid,
    )

    response = await authenticate_request(request, call_next)

    assert response.status_code == 200
    assert response.body == b"private ok"
    assert called["value"] is True
    assert captured_user["value"] == "user@example.com"


# ===================== TESTES DA DEPENDENCY get_current_user_from_token =====================


class FakeCredentials:
    """Simula HTTPAuthorizationCredentials"""

    def __init__(self, token: str):
        self.credentials = token


@pytest.mark.anyio
async def test_get_current_user_from_token_valid(monkeypatch):
    # TokenHelper.get_current_user sempre retorna um usuário válido
    monkeypatch.setattr(
        "src.Helper.SecurityHelper.TokenHelper",
        FakeTokenHelperValid,
    )

    # Mocka também o SignInHelper para não bater no banco
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            u = TokenModel.TokenModel()
            u.UserId = 123
            u.KindOfUser = "doador"
            return u

    monkeypatch.setattr(
        "src.Helper.SecurityHelper.SignInHelper",
        FakeSignInHelper,
    )

    creds = FakeCredentials("token-valido")

    user = await get_current_user_from_token(creds)

    # Agora get_current_user_from_token retorna um TokenModel, não mais string
    assert isinstance(user, TokenModel.TokenModel)
    assert user.UserId == 123
    assert user.KindOfUser == "doador"


@pytest.mark.anyio
async def test_get_current_user_from_token_invalid(monkeypatch):
    # TokenHelper.get_current_user sempre retorna None
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            # Ignora o email e devolve um TokenModel válido (não será usado neste teste)
            u = TokenModel.TokenModel()
            u.UserId = 123
            u.KindOfUser = "doador"
            return u

    monkeypatch.setattr(
        "src.Helper.SecurityHelper.SignInHelper",
        FakeSignInHelper,
    )

    monkeypatch.setattr(
        "src.Helper.SecurityHelper.TokenHelper",
        FakeTokenHelperInvalid,
    )

    creds = FakeCredentials("token-invalido")

    with pytest.raises(HTTPException) as exc:
        await get_current_user_from_token(creds)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token expired or invalid"
