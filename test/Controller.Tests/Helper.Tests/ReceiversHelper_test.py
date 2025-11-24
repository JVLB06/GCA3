import pytest

from src.Helper.ReceiversHelper import ReceiversHelper


# ===================== FAKES DE CURSOR E CONEXÃO =====================


class FakeCursor:
    def __init__(self):
        self.executed = []
        self._rows = []
        self.closed = False
        self.raise_on_execute = None
        self.to_fetch_one = None  # para validate_cause_id

    def execute(self, query, params=None):
        if self.raise_on_execute:
            raise self.raise_on_execute
        self.executed.append((query, params))

    def fetchall(self):
        return self._rows

    def fetchone(self):
        # usado em validate_cause_id
        return self.to_fetch_one

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


# ===================== TESTES DE get_receivers =====================


def make_helper_with_rows(rows, monkeypatch):
    """
    Cria um ReceiversHelper que, ao chamar Connection(),
    devolve uma FakeConnection com uma FakeCursor contendo 'rows'.
    """
    cursor = FakeCursor()
    cursor._rows = rows
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    monkeypatch.setattr(ReceiversHelper, "Connection", fake_connection)

    helper = ReceiversHelper()
    return helper, cursor, connection


def test_get_receivers_orders_by_name_desc(monkeypatch):
    rows = [
        (1, "Zé", "ze@example.com", "123", "80000000", "desc Zé"),
        (2, "Ana", "ana@example.com", "456", "80000001", "desc Ana"),
    ]
    helper, cursor, connection = make_helper_with_rows(rows, monkeypatch)

    receivers = helper.get_receivers("name_desc")

    # Verifica SQL (não precisa ser igual, só conter ORDER BY correto)
    sql, _ = cursor.executed[0]
    assert "ORDER BY nome DESC" in sql

    assert len(receivers) == 2
    assert receivers[0].UserId == 1
    assert receivers[0].Name == "Zé"
    assert receivers[0].Email == "ze@example.com"
    assert receivers[0].Document == "123"
    assert receivers[0].Address == "80000000"
    assert receivers[0].Description == "desc Zé"

    assert receivers[1].UserId == 2
    assert receivers[1].Name == "Ana"

    assert cursor.closed is True
    assert connection.closed is True


def test_get_receivers_orders_by_created_at_desc(monkeypatch):
    rows = []
    helper, cursor, connection = make_helper_with_rows(rows, monkeypatch)

    receivers = helper.get_receivers("created_at_desc")

    sql, _ = cursor.executed[0]
    assert "ORDER BY data_cadastro DESC" in sql
    assert receivers == []
    assert cursor.closed is True
    assert connection.closed is True


def test_get_receivers_orders_by_name_asc(monkeypatch):
    rows = []
    helper, cursor, connection = make_helper_with_rows(rows, monkeypatch)

    receivers = helper.get_receivers("name_asc")

    sql, _ = cursor.executed[0]
    assert "ORDER BY nome ASC" in sql
    assert receivers == []
    assert cursor.closed is True
    assert connection.closed is True


def test_get_receivers_orders_by_created_at_asc(monkeypatch):
    rows = []
    helper, cursor, connection = make_helper_with_rows(rows, monkeypatch)

    receivers = helper.get_receivers("created_at_asc")

    sql, _ = cursor.executed[0]
    assert "ORDER BY data_cadastro ASC" in sql
    assert receivers == []
    assert cursor.closed is True
    assert connection.closed is True


def test_get_receivers_default_query_when_param_empty(monkeypatch):
    rows = []
    helper, cursor, connection = make_helper_with_rows(rows, monkeypatch)

    receivers = helper.get_receivers("")

    sql, _ = cursor.executed[0]
    # não deve ter ORDER BY na query final
    assert "ORDER BY" not in sql
    assert receivers == []
    assert cursor.closed is True
    assert connection.closed is True


def test_get_receivers_default_query_when_param_none(monkeypatch):
    rows = []
    helper, cursor, connection = make_helper_with_rows(rows, monkeypatch)

    receivers = helper.get_receivers(None)

    sql, _ = cursor.executed[0]
    assert "ORDER BY" not in sql
    assert receivers == []
    assert cursor.closed is True
    assert connection.closed is True


# ===================== TESTES DE validate_cause_id =====================


def test_validate_cause_id_returns_true_when_exists(monkeypatch):
    cursor = FakeCursor()
    cursor.to_fetch_one = (10,)  # qualquer valor não None
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    monkeypatch.setattr(ReceiversHelper, "Connection", fake_connection)

    helper = ReceiversHelper()

    result = helper.validate_cause_id(10)

    assert result is True
    # confere SQL
    sql, params = cursor.executed[0]
    assert "id_usuario = %s" in sql
    assert params == (10,)
    assert cursor.closed is True
    assert connection.closed is True


def test_validate_cause_id_returns_false_when_not_found(monkeypatch):
    cursor = FakeCursor()
    cursor.to_fetch_one = None  # não encontrado
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    monkeypatch.setattr(ReceiversHelper, "Connection", fake_connection)

    helper = ReceiversHelper()

    result = helper.validate_cause_id(99)

    assert result is False
    assert cursor.closed is True
    assert connection.closed is True


def test_validate_cause_id_returns_false_when_connection_fails(monkeypatch):
    def fake_connection(self):
        return None  # simula falha de conexão

    monkeypatch.setattr(ReceiversHelper, "Connection", fake_connection)

    helper = ReceiversHelper()

    result = helper.validate_cause_id(10)

    assert result is False  # early return sem tentar query


def test_validate_cause_id_returns_false_on_exception(monkeypatch):
    cursor = FakeCursor()
    cursor.raise_on_execute = Exception("db error")
    connection = FakeConnection(cursor)

    def fake_connection(self):
        return connection

    monkeypatch.setattr(ReceiversHelper, "Connection", fake_connection)

    helper = ReceiversHelper()

    result = helper.validate_cause_id(10)

    assert result is False
    # mesmo com erro, finally deve fechar cursor e conexão
    assert cursor.closed is True
    assert connection.closed is True
