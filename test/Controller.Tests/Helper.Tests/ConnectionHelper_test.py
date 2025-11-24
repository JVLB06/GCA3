import psycopg2 as pg
import pytest

from src.Helper.ConnectionHelper import ConnectionHelper


class FakeConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_connection_success(monkeypatch):
    helper = ConnectionHelper()
    captured_kwargs = {}

    def fake_connect(**kwargs):
        # guarda os argumentos usados na chamada
        captured_kwargs.update(kwargs)
        return FakeConnection()

    # monkeypatch no pg.connect DENTRO do módulo ConnectionHelper
    monkeypatch.setattr(
        "src.Helper.ConnectionHelper.pg.connect",
        fake_connect,
    )

    conn = helper.Connection()

    # Deve retornar uma conexão fake
    assert isinstance(conn, FakeConnection)

    # Verifica se os parâmetros foram passados corretamente
    assert captured_kwargs["database"] == helper.Database
    assert captured_kwargs["user"] == helper.User
    assert captured_kwargs["password"] == helper.Password
    assert captured_kwargs["host"] == helper.Host
    assert captured_kwargs["port"] == helper.Port


def test_connection_failure_returns_none(monkeypatch, capsys):
    helper = ConnectionHelper()

    def fake_connect(**kwargs):
        # Simula erro de conexão do psycopg2
        raise pg.Error("Connection failed")

    monkeypatch.setattr(
        "src.Helper.ConnectionHelper.pg.connect",
        fake_connect,
    )

    conn = helper.Connection()

    # Deve retornar None quando der erro
    assert conn is None

    # Opcional: checar se logou a mensagem de erro no print
    captured = capsys.readouterr()
    assert "Error connecting to database" in captured.out


def test_close_connection_calls_close():
    helper = ConnectionHelper()
    conn = FakeConnection()

    helper.CloseConnection(conn)

    assert conn.closed is True


def test_close_connection_does_nothing_if_none():
    helper = ConnectionHelper()

    # Só garantir que não levanta exceção
    helper.CloseConnection(None)
