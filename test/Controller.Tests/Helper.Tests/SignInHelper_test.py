import pytest
from fastapi import HTTPException
import requests

from src.Helper.SignInHelper import SignInHelper, pg


# ===================== FAKES DE CONEXÃO E CURSOR =====================


class FakeCursor:
    def __init__(self):
        self.to_fetch = []
        self.executed = []
        self.closed = False
        self.raise_on_execute = None

    def execute(self, query, params=None):
        if self.raise_on_execute:
            raise self.raise_on_execute
        self.executed.append((query, params))

    def fetchone(self):
        if self.to_fetch:
            return self.to_fetch.pop(0)
        return None

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


# ===================== TESTES DE SignIn =====================


def test_signin_returns_true_when_user_exists(monkeypatch):
    cursor = FakeCursor()
    cursor.to_fetch = [(1,)]  # COUNT(1) = 1
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.closed = True

    monkeypatch.setattr(SignInHelper, "Connection", fake_connection)
    monkeypatch.setattr(SignInHelper, "CloseConnection", fake_close)

    helper = SignInHelper()
    # objeto simples com atributos necessários
    params = type("LoginParams", (), {"Username": "user@test.com", "Password": "123"})()

    result = helper.SignIn(params)

    assert result is True
    assert cursor.closed is True
    assert connection.closed is True


def test_signin_returns_false_when_user_not_found(monkeypatch):
    cursor = FakeCursor()
    cursor.to_fetch = [(0,)]  # COUNT(1) = 0
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.closed = True

    monkeypatch.setattr(SignInHelper, "Connection", fake_connection)
    monkeypatch.setattr(SignInHelper, "CloseConnection", fake_close)

    helper = SignInHelper()
    params = type("LoginParams", (), {"Username": "notfound@test.com", "Password": "123"})()

    result = helper.SignIn(params)

    assert result is False
    assert cursor.closed is True
    assert connection.closed is True


def test_signin_raises_http_500_if_connection_fails(monkeypatch):
    def fake_connection(self):
        return None

    monkeypatch.setattr(SignInHelper, "Connection", fake_connection)

    helper = SignInHelper()
    params = type("LoginParams", (), {"Username": "user@test.com", "Password": "123"})()

    with pytest.raises(HTTPException) as exc:
        helper.SignIn(params)

    assert exc.value.status_code == 500
    assert exc.value.detail == "Database connection failed"


def test_signin_returns_false_on_pg_error(monkeypatch):
    cursor = FakeCursor()
    cursor.raise_on_execute = pg.Error("db error")  # será capturado no except pg.Error
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.closed = True

    monkeypatch.setattr(SignInHelper, "Connection", fake_connection)
    monkeypatch.setattr(SignInHelper, "CloseConnection", fake_close)

    helper = SignInHelper()
    params = type("LoginParams", (), {"Username": "user@test.com", "Password": "123"})()

    result = helper.SignIn(params)

    assert result is False
    assert connection.closed is True


# ===================== TESTES DE Cadastrate =====================


def test_cadastrate_success(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.closed = True

    monkeypatch.setattr(SignInHelper, "Connection", fake_connection)
    monkeypatch.setattr(SignInHelper, "CloseConnection", fake_close)

    helper = SignInHelper()
    params = type(
        "CadastrateParams",
        (),
        {
            "Name": "Teste",
            "Email": "user@test.com",
            "Password": "123",
            "IsReceiver": "doador",
            "Document": "123",
            "Address": "85123000",
            "Cause": "Ajuda",
        },
    )()

    result = helper.Cadastrate(params)

    assert result is True
    assert connection.committed is True
    assert cursor.closed is True
    assert connection.closed is True


def test_cadastrate_returns_false_on_pg_error(monkeypatch):
    cursor = FakeCursor()
    cursor.raise_on_execute = pg.Error("db error")
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.closed = True

    monkeypatch.setattr(SignInHelper, "Connection", fake_connection)
    monkeypatch.setattr(SignInHelper, "CloseConnection", fake_close)

    helper = SignInHelper()
    params = type(
        "CadastrateParams",
        (),
        {
            "Name": "Teste",
            "Email": "user@test.com",
            "Password": "123",
            "IsReceiver": "doador",
            "Document": "123",
            "Address": "85123000",
            "Cause": "Ajuda",
        },
    )()

    result = helper.Cadastrate(params)

    assert result is False
    # mesmo com erro, CloseConnection deve ser chamado
    assert connection.closed is True


def test_cadastrate_raises_http_500_if_connection_fails(monkeypatch):
    def fake_connection(self):
        return None

    monkeypatch.setattr(SignInHelper, "Connection", fake_connection)

    helper = SignInHelper()
    params = type(
        "CadastrateParams",
        (),
        {
            "Name": "Teste",
            "Email": "user@test.com",
            "Password": "123",
            "IsReceiver": "doador",
            "Document": "123",
            "Address": "85123000",
            "Cause": "Ajuda",
        },
    )()

    with pytest.raises(HTTPException) as exc:
        helper.Cadastrate(params)

    assert exc.value.status_code == 500
    assert exc.value.detail == "Database connection failed"


# ===================== TESTES DE GetKindOfUser =====================


def test_get_kind_of_user_success(monkeypatch):
    cursor = FakeCursor()
    cursor.to_fetch = [(10, "receptor")]
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.closed = True

    monkeypatch.setattr(SignInHelper, "Connection", fake_connection)
    monkeypatch.setattr(SignInHelper, "CloseConnection", fake_close)

    helper = SignInHelper()

    result = helper.GetKindOfUser("user@test.com")

    assert result.UserId == 10
    assert result.KindOfUser == "receptor"
    assert cursor.closed is True
    assert connection.closed is True


def test_get_kind_of_user_raises_404_if_not_found(monkeypatch):
    cursor = FakeCursor()
    cursor.to_fetch = [None]  # fetchone() sem resultado
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.closed = True

    monkeypatch.setattr(SignInHelper, "Connection", fake_connection)
    monkeypatch.setattr(SignInHelper, "CloseConnection", fake_close)

    helper = SignInHelper()

    with pytest.raises(HTTPException) as exc:
        helper.GetKindOfUser("missing@test.com")

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found in database"
    assert cursor.closed is True
    assert connection.closed is True


def test_get_kind_of_user_raises_500_if_connection_fails(monkeypatch):
    def fake_connection(self):
        return None

    monkeypatch.setattr(SignInHelper, "Connection", fake_connection)

    helper = SignInHelper()

    with pytest.raises(HTTPException) as exc:
        helper.GetKindOfUser("user@test.com")

    assert exc.value.status_code == 500
    assert exc.value.detail == "Database connection failed"


# ===================== TESTES DE ValidateAddress =====================


def test_validate_address_returns_false_if_invalid_length():
    helper = SignInHelper()

    assert helper.ValidateAddress("123") is False  # menos de 8 dígitos
    assert helper.ValidateAddress("123456789") is False  # mais de 8 dígitos


def test_validate_address_success(monkeypatch):
    helper = SignInHelper()

    class FakeResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data

        def json(self):
            return self._json

    class FakeSession:
        def __init__(self, response):
            self._response = response

        def get(self, url, timeout=5):
            return self._response

    # CEP válido e ativo
    resp = FakeResponse(200, {"logradouro": "Rua X", "erro": False})
    monkeypatch.setattr(
        "src.Helper.SignInHelper.requests.Session",
        lambda: FakeSession(resp),
    )

    assert helper.ValidateAddress("85123-000") is True


def test_validate_address_returns_false_if_viacep_returns_erro(monkeypatch):
    helper = SignInHelper()

    class FakeResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data

        def json(self):
            return self._json

    class FakeSession:
        def __init__(self, response):
            self._response = response

        def get(self, url, timeout=5):
            return self._response

    # ViaCEP responde {"erro": true}
    resp = FakeResponse(200, {"erro": True})
    monkeypatch.setattr(
        "src.Helper.SignInHelper.requests.Session",
        lambda: FakeSession(resp),
    )

    assert helper.ValidateAddress("85123000") is False


def test_validate_address_returns_false_on_non_200_status(monkeypatch):
    helper = SignInHelper()

    class FakeResponse:
        def __init__(self, status_code):
            self.status_code = status_code

        def json(self):
            return {}

    class FakeSession:
        def __init__(self, response):
            self._response = response

        def get(self, url, timeout=5):
            return self._response

    resp = FakeResponse(500)
    monkeypatch.setattr(
        "src.Helper.SignInHelper.requests.Session",
        lambda: FakeSession(resp),
    )

    assert helper.ValidateAddress("85123000") is False


def test_validate_address_returns_false_on_request_exception(monkeypatch):
    helper = SignInHelper()

    class FakeSession:
        def get(self, url, timeout=5):
            raise requests.RequestException("network error")

    monkeypatch.setattr(
        "src.Helper.SignInHelper.requests.Session",
        lambda: FakeSession(),
    )

    assert helper.ValidateAddress("85123000") is False
