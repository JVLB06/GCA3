import pytest
from fastapi import HTTPException

from src.Helper.FavoritesHelper import FavoriteHelper
from src.Model.AddFavoriteModel import AddFavoriteModel
from src.Model.FavoriteModel import FavoriteModel


# ==========================
# Fakes de conexão / cursor
# ==========================

class FakeCursor:
    def __init__(
        self,
        fetchone_results=None,
        fetchall_result=None,
        raise_on_execute=False,
        raise_on_second_execute=False,
    ):
        # Lista de resultados para cada chamada de fetchone()
        self.fetchone_results = list(fetchone_results or [])
        # Resultado único para fetchall()
        self.fetchall_result = fetchall_result or []
        # Flags para simular erro
        self.raise_on_execute = raise_on_execute
        self.raise_on_second_execute = raise_on_second_execute

        self.execute_calls = []  # histórico das execuções (query, params)
        self.execute_count = 0

    def execute(self, query, params=None):
        self.execute_count += 1
        self.execute_calls.append((query, params))

        # Erro genérico em qualquer execute
        if self.raise_on_execute:
            raise Exception("DB error")

        # Erro apenas na segunda chamada (útil para DELETE, por exemplo)
        if self.raise_on_second_execute and self.execute_count == 2:
            raise Exception("DB error on second execute")

    def fetchone(self):
        if self.fetchone_results:
            return self.fetchone_results.pop(0)
        return None

    def fetchall(self):
        return self.fetchall_result


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

    def close(self):
        self.closed = True


# ==========================
# Testes de add_favorite
# ==========================

def test_add_favorite_success(monkeypatch):
    # SELECT não encontra favorito -> INSERT -> commit
    cursor = FakeCursor(fetchone_results=[None])
    connection = FakeConnection(cursor)

    # Monkeypatch da Connection do helper
    monkeypatch.setattr(
        "src.Helper.FavoritesHelper.FavoriteHelper.Connection",
        lambda self: connection,
    )

    helper = FavoriteHelper()
    fav_info = AddFavoriteModel(CauseId=123, UserId=10)

    result = helper.add_favorite(fav_info)

    assert result["message"] == "Cause with ID 123 favorited successfully"
    # Verifica que houve commit e não rollback
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.closed is True

    # Garante que o INSERT foi chamado
    assert any(
        "INSERT INTO favoritos" in call[0] for call in cursor.execute_calls
    )


def test_add_favorite_conflict_when_already_exists(monkeypatch):
    # SELECT encontra um registro -> deve levantar HTTPException 409
    cursor = FakeCursor(fetchone_results=[(1,)])
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.FavoritesHelper.FavoriteHelper.Connection",
        lambda self: connection,
    )

    helper = FavoriteHelper()
    fav_info = AddFavoriteModel(CauseId=123, UserId=10)

    with pytest.raises(HTTPException) as exc_info:
        helper.add_favorite(fav_info)

    err = exc_info.value
    assert err.status_code == 409
    assert err.detail == "Cause already favorited"

    # Sem commit nem rollback nesse fluxo
    assert connection.committed is False
    assert connection.rolled_back is False
    assert connection.closed is True


def test_add_favorite_database_connection_failed(monkeypatch):
    # Connection() retorna None
    monkeypatch.setattr(
        "src.Helper.FavoritesHelper.FavoriteHelper.Connection",
        lambda self: None,
    )

    helper = FavoriteHelper()
    fav_info = AddFavoriteModel(CauseId=123, UserId=10)

    with pytest.raises(HTTPException) as exc_info:
        helper.add_favorite(fav_info)

    err = exc_info.value
    assert err.status_code == 500
    assert err.detail == "Database connection failed"


def test_add_favorite_generic_db_error_triggers_rollback(monkeypatch):
    # Qualquer erro em execute deve cair no except Exception, dar rollback e re-levantar HTTPException 500
    cursor = FakeCursor(fetchone_results=[None], raise_on_execute=True)
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.FavoritesHelper.FavoriteHelper.Connection",
        lambda self: connection,
    )

    helper = FavoriteHelper()
    fav_info = AddFavoriteModel(CauseId=123, UserId=10)

    with pytest.raises(HTTPException) as exc_info:
        helper.add_favorite(fav_info)

    err = exc_info.value
    assert err.status_code == 500
    assert "Error favoriting cause" in err.detail

    assert connection.committed is False
    assert connection.rolled_back is True
    assert connection.closed is True


# ==========================
# Testes de remove_favorite
# ==========================

def test_remove_favorite_success(monkeypatch):
    # SELECT encontra favorito -> DELETE -> commit
    cursor = FakeCursor(fetchone_results=[(1,)])
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.FavoritesHelper.FavoriteHelper.Connection",
        lambda self: connection,
    )

    helper = FavoriteHelper()
    fav_id = 5

    result = helper.remove_favorite(fav_id)

    assert result["message"] == f"Favorite with ID {fav_id} removed successfully"
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.closed is True

    # Confere que teve DELETE
    assert any(
        "DELETE FROM favoritos" in call[0] for call in cursor.execute_calls
    )


def test_remove_favorite_not_found(monkeypatch):
    # SELECT não encontra nada -> 404
    cursor = FakeCursor(fetchone_results=[None])
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.FavoritesHelper.FavoriteHelper.Connection",
        lambda self: connection,
    )

    helper = FavoriteHelper()

    with pytest.raises(HTTPException) as exc_info:
        helper.remove_favorite(99)

    err = exc_info.value
    assert err.status_code == 404
    assert err.detail == "Favorite not found"

    assert connection.committed is False
    assert connection.rolled_back is False
    assert connection.closed is True


def test_remove_favorite_database_connection_failed(monkeypatch):
    monkeypatch.setattr(
        "src.Helper.FavoritesHelper.FavoriteHelper.Connection",
        lambda self: None,
    )

    helper = FavoriteHelper()

    with pytest.raises(HTTPException) as exc_info:
        helper.remove_favorite(1)

    err = exc_info.value
    assert err.status_code == 500
    assert err.detail == "Database connection failed"


def test_remove_favorite_generic_db_error_triggers_rollback(monkeypatch):
    # Erro na segunda execução (DELETE, por exemplo)
    cursor = FakeCursor(
        fetchone_results=[(1,)],
        raise_on_second_execute=True,
    )
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.FavoritesHelper.FavoriteHelper.Connection",
        lambda self: connection,
    )

    helper = FavoriteHelper()

    with pytest.raises(HTTPException) as exc_info:
        helper.remove_favorite(1)

    err = exc_info.value
    assert err.status_code == 500
    assert "Error removing favorite" in err.detail
    assert connection.committed is False
    assert connection.rolled_back is True
    assert connection.closed is True


# ==========================
# Testes de list_favorites
# ==========================

def test_list_favorites_success(monkeypatch):
    # Simula retorno de duas linhas da query
    rows = [
        ("Cause 1", "Desc 1", "Address 1", "Doc1"),
        ("Cause 2", "Desc 2", "Address 2", "Doc2"),
    ]
    cursor = FakeCursor(fetchall_result=rows)
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.FavoritesHelper.FavoriteHelper.Connection",
        lambda self: connection,
    )

    helper = FavoriteHelper()
    user_id = 10

    favorites = helper.list_favorites(user_id)

    assert isinstance(favorites, list)
    assert len(favorites) == 2
    assert all(isinstance(f, FavoriteModel) for f in favorites)

    assert favorites[0].CauseName == "Cause 1"
    assert favorites[0].CauseDescription == "Desc 1"
    assert favorites[0].CauseAddress == "Address 1"
    assert favorites[0].CauseDocument == "Doc1"

    assert favorites[1].CauseName == "Cause 2"
    assert favorites[1].CauseDescription == "Desc 2"
    assert favorites[1].CauseAddress == "Address 2"
    assert favorites[1].CauseDocument == "Doc2"

    assert connection.closed is True


def test_list_favorites_empty_list(monkeypatch):
    cursor = FakeCursor(fetchall_result=[])
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.FavoritesHelper.FavoriteHelper.Connection",
        lambda self: connection,
    )

    helper = FavoriteHelper()
    favorites = helper.list_favorites(user_id=10)

    assert favorites == []
    assert connection.closed is True


def test_list_favorites_database_connection_failed(monkeypatch):
    monkeypatch.setattr(
        "src.Helper.FavoritesHelper.FavoriteHelper.Connection",
        lambda self: None,
    )

    helper = FavoriteHelper()

    with pytest.raises(HTTPException) as exc_info:
        helper.list_favorites(user_id=10)

    err = exc_info.value
    assert err.status_code == 500
    assert err.detail == "Database connection failed"


def test_list_favorites_generic_db_error(monkeypatch):
    cursor = FakeCursor(raise_on_execute=True)
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        "src.Helper.FavoritesHelper.FavoriteHelper.Connection",
        lambda self: connection,
    )

    helper = FavoriteHelper()

    with pytest.raises(HTTPException) as exc_info:
        helper.list_favorites(user_id=10)

    err = exc_info.value
    assert err.status_code == 500
    assert "Error listing favorites" in err.detail
    assert connection.closed is True
