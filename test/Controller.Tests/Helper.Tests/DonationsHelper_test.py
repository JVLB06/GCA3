import pytest
from fastapi import HTTPException

from src.Helper.DonationsHelper import DonationsHelper
from src.Model.DonationModel import DonationModel
from src.Model.ListDonationModel import ListDonationModel


# ======================
# Fakes de cursor/conexão
# ======================

class FakeCursor:
    def __init__(self, fetchall_result=None, raise_on_execute=False):
        self.fetchall_result = fetchall_result or []
        self.raise_on_execute = raise_on_execute
        self.execute_calls = []
        self.closed = False

    def execute(self, query, params=None):
        self.execute_calls.append((query, params))
        if self.raise_on_execute:
            raise Exception("DB error in execute")

    def fetchall(self):
        return self.fetchall_result

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


# =========================
# list_donations_by_user
# =========================

def test_list_donations_by_user_success(monkeypatch):
    # Linhas simulando o resultado do SELECT:
    # (id_doacao, Doador, Receptor, valor, mensagem, data_doacao)
    rows = [
        (1, "Doador 1", "Receptor 1", 100.0, "Msg 1", "2024-01-01"),
        (2, "Doador 2", "Receptor 2", 250.5, "Msg 2", "2024-02-10"),
    ]
    cursor = FakeCursor(fetchall_result=rows)
    connection = FakeConnection(cursor)

    # Mock da Connection do helper
    monkeypatch.setattr(
        "src.Helper.DonationsHelper.DonationsHelper.Connection",
        lambda self: connection,
    )

    # Mock da CloseConnection do helper para usar o close() do FakeConnection
    monkeypatch.setattr(
        "src.Helper.DonationsHelper.DonationsHelper.CloseConnection",
        lambda self, conn: conn.close(),
    )

    helper = DonationsHelper()
    result = helper.list_donations_by_user(user_id=10)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(d, ListDonationModel) for d in result)

    # Mapeamento conforme o helper:
    # DonotionId=row[0], DonorName=row[1], ReceiverName=row[2],
    # Amount=row[3], Message=row[4], Date=row[5]
    first = result[0]
    assert first.DonationId == 1
    assert first.DonorName == "Doador 1"
    assert first.ReceiverName == "Receptor 1"
    assert first.Amount == 100.0
    assert first.Message == "Msg 1"
    assert first.Date == "2024-01-01"

    second = result[1]
    assert second.DonationId == 2
    assert second.DonorName == "Doador 2"
    assert second.ReceiverName == "Receptor 2"
    assert second.Amount == 250.5
    assert second.Message == "Msg 2"
    assert second.Date == "2024-02-10"

    # Garante que recursos foram fechados
    assert cursor.closed is True
    assert connection.closed is True


def test_list_donations_by_user_db_error(monkeypatch):
    cursor = FakeCursor(raise_on_execute=True)
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.DonationsHelper.DonationsHelper.Connection",
        lambda self: connection,
    )
    monkeypatch.setattr(
        "src.Helper.DonationsHelper.DonationsHelper.CloseConnection",
        lambda self, conn: conn.close(),
    )

    helper = DonationsHelper()

    with pytest.raises(HTTPException) as exc_info:
        helper.list_donations_by_user(user_id=10)

    err = exc_info.value
    assert err.status_code == 500
    assert "DB error in execute" in err.detail

    # Mesmo em caso de erro o finally deve fechar
    assert cursor.closed is True
    assert connection.closed is True


# =========================
# list_donations_received
# =========================

def test_list_donations_received_success(monkeypatch):
    rows = [
        (10, "Doador A", "Receptor A", 300.0, "Msg A", "2024-03-05"),
    ]
    cursor = FakeCursor(fetchall_result=rows)
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.DonationsHelper.DonationsHelper.Connection",
        lambda self: connection,
    )
    monkeypatch.setattr(
        "src.Helper.DonationsHelper.DonationsHelper.CloseConnection",
        lambda self, conn: conn.close(),
    )

    helper = DonationsHelper()
    result = helper.list_donations_received(receiver_id=99)

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], ListDonationModel)

    d = result[0]
    assert d.DonationId == 10
    assert d.DonorName == "Doador A"
    assert d.ReceiverName == "Receptor A"
    assert d.Amount == 300.0
    assert d.Message == "Msg A"
    assert d.Date == "2024-03-05"

    assert cursor.closed is True
    assert connection.closed is True


def test_list_donations_received_db_error(monkeypatch):
    cursor = FakeCursor(raise_on_execute=True)
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.DonationsHelper.DonationsHelper.Connection",
        lambda self: connection,
    )
    monkeypatch.setattr(
        "src.Helper.DonationsHelper.DonationsHelper.CloseConnection",
        lambda self, conn: conn.close(),
    )

    helper = DonationsHelper()

    with pytest.raises(HTTPException) as exc_info:
        helper.list_donations_received(receiver_id=99)

    err = exc_info.value
    assert err.status_code == 500
    assert "DB error in execute" in err.detail

    assert cursor.closed is True
    assert connection.closed is True


# =========================
# add_donations
# =========================

def test_add_donations_success(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.DonationsHelper.DonationsHelper.Connection",
        lambda self: connection,
    )
    monkeypatch.setattr(
        "src.Helper.DonationsHelper.DonationsHelper.CloseConnection",
        lambda self, conn: conn.close(),
    )

    helper = DonationsHelper()

    donation_info = DonationModel(
        DonorId=10,
        ReceiverId=20,
        Amount=150.0,
        Message="Ajuda",
        Date="2024-01-10",
    )

    result = helper.add_donations(donation_info)

    # Método não retorna nada, apenas realiza o commit
    assert result == {"message": "Donation efetuated successfully"}
    assert connection.committed is True

    # Verifica que o INSERT foi executado com os parâmetros corretos
    assert len(cursor.execute_calls) == 1
    query, params = cursor.execute_calls[0]
    assert "INSERT INTO doacoes" in query
    assert params == (
        10,
        20,
        150.0,
        "Ajuda",
        "2024-01-10",
    )

    assert cursor.closed is True
    assert connection.closed is True


def test_add_donations_db_error(monkeypatch):
    cursor = FakeCursor(raise_on_execute=True)
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.DonationsHelper.DonationsHelper.Connection",
        lambda self: connection,
    )
    monkeypatch.setattr(
        "src.Helper.DonationsHelper.DonationsHelper.CloseConnection",
        lambda self, conn: conn.close(),
    )

    helper = DonationsHelper()

    donation_info = DonationModel(
        DonorId=10,
        ReceiverId=20,
        Amount=150.0,
        Message="Ajuda",
        Date="2024-01-10",
    )

    with pytest.raises(HTTPException) as exc_info:
        helper.add_donations(donation_info)

    err = exc_info.value
    assert err.status_code == 500
    assert "DB error in execute" in err.detail

    # Não deve ter commit em caso de erro
    assert connection.committed is False
    assert cursor.closed is True
    assert connection.closed is True
