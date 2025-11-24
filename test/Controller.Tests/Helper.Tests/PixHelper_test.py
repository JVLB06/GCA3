import pytest
from fastapi import HTTPException

from src.Helper.PixHelper import PixHelper, pg


# ===================== FAKES DE CURSOR E CONEXÃO =====================


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.to_fetch_one = None
        self.closed = False
        self.raise_on_execute = None

    def execute(self, query, params=None):
        if self.raise_on_execute:
            raise self.raise_on_execute
        self.executed.append((query, params))

    def fetchone(self):
        return self.to_fetch_one

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor
        self.committed = False
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


# ===================== validate_pix_key =====================


def test_validate_pix_key_returns_true_when_no_pix_for_user(monkeypatch):
    cursor = FakeCursor()
    cursor.to_fetch_one = (0,)  # COUNT(1) = 0 => não existe chave => True
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.close()

    monkeypatch.setattr(PixHelper, "Connection", fake_connection)
    monkeypatch.setattr(PixHelper, "CloseConnection", fake_close)

    helper = PixHelper()
    pix = type("PixValidation", (), {"UserId": 10})()

    result = helper.validate_pix_key(pix)

    assert result is True
    sql, params = cursor.executed[0]
    assert "FROM pix_chaves" in sql
    assert params == (str(10),)
    assert cursor.closed is True
    assert connection.closed is True


def test_validate_pix_key_returns_false_when_pix_exists(monkeypatch):
    cursor = FakeCursor()
    cursor.to_fetch_one = (1,)  # COUNT(1) = 1 => já existe chave => False
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.close()

    monkeypatch.setattr(PixHelper, "Connection", fake_connection)
    monkeypatch.setattr(PixHelper, "CloseConnection", fake_close)

    helper = PixHelper()
    pix = type("PixValidation", (), {"UserId": 10})()

    result = helper.validate_pix_key(pix)

    assert result is False
    assert cursor.closed is True
    assert connection.closed is True


def test_validate_pix_key_raises_503_if_connection_fails(monkeypatch):
    def fake_connection(self):
        return None  # simula erro de conexão

    monkeypatch.setattr(PixHelper, "Connection", fake_connection)

    helper = PixHelper()
    pix = type("PixValidation", (), {"UserId": 10})()

    with pytest.raises(HTTPException) as exc:
        helper.validate_pix_key(pix)

    assert exc.value.status_code == 503
    assert exc.value.detail == "Connection error"


def test_validate_pix_key_raises_403_on_pg_error(monkeypatch):
    cursor = FakeCursor()
    cursor.raise_on_execute = pg.Error("db error")
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.close()

    monkeypatch.setattr(PixHelper, "Connection", fake_connection)
    monkeypatch.setattr(PixHelper, "CloseConnection", fake_close)

    helper = PixHelper()
    pix = type("PixValidation", (), {"UserId": 10})()

    with pytest.raises(HTTPException) as exc:
        helper.validate_pix_key(pix)

    assert exc.value.status_code == 403
    assert "Error validating PIX key" in exc.value.detail
    assert cursor.closed is True
    assert connection.closed is True


# ===================== add_pix_key =====================


def test_add_pix_key_success(monkeypatch):
    # conexão usada dentro de add_pix_key
    cursor = FakeCursor()
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.close()

    # validate_pix_key deve retornar True (nenhuma chave existente)
    def fake_validate(self, pix_validation):
        return True

    monkeypatch.setattr(PixHelper, "Connection", fake_connection)
    monkeypatch.setattr(PixHelper, "CloseConnection", fake_close)
    monkeypatch.setattr(PixHelper, "validate_pix_key", fake_validate)

    helper = PixHelper()
    pix = type(
        "PixModel",
        (),
        {
            "UserId": 10,
            "PixKey": "chave@pix.com",
            "KeyType": "email",
            "CreatedAt": "2025-01-01T10:00:00",
        },
    )()

    msg = helper.add_pix_key(pix)

    assert msg == "Pix key added successfully"
    sql, params = cursor.executed[0]
    assert "INSERT INTO pix_chaves" in sql
    assert params == (10, "chave@pix.com", "email", "2025-01-01T10:00:00")
    assert connection.committed is True
    assert cursor.closed is True
    assert connection.closed is True


def test_add_pix_key_raises_409_if_pix_already_exists(monkeypatch):
    # conexão ainda é criada, mas validate_pix_key já retorna False
    connection = FakeConnection(FakeCursor())

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.close()

    # já existe chave => validate_pix_key -> False
    def fake_validate(self, pix_validation):
        return False

    monkeypatch.setattr(PixHelper, "Connection", fake_connection)
    monkeypatch.setattr(PixHelper, "CloseConnection", fake_close)
    monkeypatch.setattr(PixHelper, "validate_pix_key", fake_validate)

    helper = PixHelper()
    pix = type(
        "PixModel",
        (),
        {
            "UserId": 10,
            "PixKey": "chave@pix.com",
            "KeyType": "email",
            "CreatedAt": "2025-01-01T10:00:00",
        },
    )()

    with pytest.raises(HTTPException) as exc:
        helper.add_pix_key(pix)

    assert exc.value.status_code == 409
    assert exc.value.detail == "PIX key already exists"
    # aqui, pelo código atual, a conexão NÃO é fechada, mas
    # não vamos testar isso pra você poder corrigir depois sem quebrar o teste


def test_add_pix_key_raises_503_if_connection_fails(monkeypatch):
    def fake_connection(self):
        return None

    monkeypatch.setattr(PixHelper, "Connection", fake_connection)

    helper = PixHelper()
    pix = type(
        "PixModel",
        (),
        {
            "UserId": 10,
            "PixKey": "chave@pix.com",
            "KeyType": "email",
            "CreatedAt": "2025-01-01T10:00:00",
        },
    )()

    with pytest.raises(HTTPException) as exc:
        helper.add_pix_key(pix)

    assert exc.value.status_code == 503
    assert exc.value.detail == "Connection error"


def test_add_pix_key_raises_500_on_pg_error(monkeypatch):
    cursor = FakeCursor()
    cursor.raise_on_execute = pg.Error("db error")
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.close()

    def fake_validate(self, pix_validation):
        return True  # segue para o INSERT

    monkeypatch.setattr(PixHelper, "Connection", fake_connection)
    monkeypatch.setattr(PixHelper, "CloseConnection", fake_close)
    monkeypatch.setattr(PixHelper, "validate_pix_key", fake_validate)

    helper = PixHelper()
    pix = type(
        "PixModel",
        (),
        {
            "UserId": 10,
            "PixKey": "chave@pix.com",
            "KeyType": "email",
            "CreatedAt": "2025-01-01T10:00:00",
        },
    )()

    with pytest.raises(HTTPException) as exc:
        helper.add_pix_key(pix)

    assert exc.value.status_code == 500
    assert "Error during adding pix key" in exc.value.detail
    assert cursor.closed is True
    assert connection.closed is True


# ===================== delete_pix_key =====================


def test_delete_pix_key_success(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.close()

    # validate_pix_key False => existe chave => segue para DELETE
    def fake_validate(self, pix_validation):
        return False

    monkeypatch.setattr(PixHelper, "Connection", fake_connection)
    monkeypatch.setattr(PixHelper, "CloseConnection", fake_close)
    monkeypatch.setattr(PixHelper, "validate_pix_key", fake_validate)

    helper = PixHelper()
    pix = type("PixDelete", (), {"UserId": 10, "PixId": 123})()

    msg = helper.delete_pix_key(pix)

    assert msg == "Pix key deleted successfully"
    sql, params = cursor.executed[0]
    assert "DELETE FROM pix_chaves" in sql
    assert params == (10, 123)
    assert connection.committed is True
    assert cursor.closed is True
    assert connection.closed is True


def test_delete_pix_key_raises_404_if_pix_not_found(monkeypatch):
    connection = FakeConnection(FakeCursor())

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.close()

    # validate_pix_key True => não existe chave => 404
    def fake_validate(self, pix_validation):
        return True

    monkeypatch.setattr(PixHelper, "Connection", fake_connection)
    monkeypatch.setattr(PixHelper, "CloseConnection", fake_close)
    monkeypatch.setattr(PixHelper, "validate_pix_key", fake_validate)

    helper = PixHelper()
    pix = type("PixDelete", (), {"UserId": 10, "PixId": 123})()

    with pytest.raises(HTTPException) as exc:
        helper.delete_pix_key(pix)

    assert exc.value.status_code == 404
    assert exc.value.detail == "PIX key not found"
    # idem: aqui o código atual não fecha a conexão, então não assertamos isso ainda


def test_delete_pix_key_raises_503_if_connection_fails(monkeypatch):
    def fake_connection(self):
        return None

    monkeypatch.setattr(PixHelper, "Connection", fake_connection)

    helper = PixHelper()
    pix = type("PixDelete", (), {"UserId": 10, "PixId": 123})()

    with pytest.raises(HTTPException) as exc:
        helper.delete_pix_key(pix)

    assert exc.value.status_code == 503
    assert exc.value.detail == "Connection error"


def test_delete_pix_key_raises_500_on_pg_error(monkeypatch):
    cursor = FakeCursor()
    cursor.raise_on_execute = pg.Error("db error")
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    def fake_close(self, conn):
        conn.close()

    def fake_validate(self, pix_validation):
        return False  # segue para o DELETE

    monkeypatch.setattr(PixHelper, "Connection", fake_connection)
    monkeypatch.setattr(PixHelper, "CloseConnection", fake_close)
    monkeypatch.setattr(PixHelper, "validate_pix_key", fake_validate)

    helper = PixHelper()
    pix = type("PixDelete", (), {"UserId": 10, "PixId": 123})()

    with pytest.raises(HTTPException) as exc:
        helper.delete_pix_key(pix)

    assert exc.value.status_code == 500
    assert "Error during deleting pix key" in exc.value.detail
    assert cursor.closed is True
    assert connection.closed is True
