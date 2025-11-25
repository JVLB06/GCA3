import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.Controller.ReceiverController import ReceiverController
from src.Helper.SecurityHelper import get_current_user_from_token


# ===================== FAKES GENÉRICOS =====================


class FakeUserData:
    def __init__(self, user_id: int, kind_of_user: str):
        self.UserId = user_id
        self.KindOfUser = kind_of_user


def make_fake_user(user_id: int, kind_of_user: str) -> FakeUserData:
    return FakeUserData(user_id, kind_of_user)


class FakeCursor:
    def __init__(self):
        self.to_fetch = []   # resultados que serão retornados por fetchone()
        self.executed = []   # SQLs executados para conferência

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        if self.to_fetch:
            return self.to_fetch.pop(0)
        return None


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


class FakePixHelper:
    def __init__(self):
        self.add_called_with = None
        self.delete_called_with = None

    def add_pix_key(self, request):
        self.add_called_with = request
        return "Pix key added"

    def delete_pix_key(self, request):
        self.delete_called_with = request
        return "Pix key deleted"


# ===================== /receiver/ =====================


def test_get_receiver_root():
    app = FastAPI()
    app.include_router(ReceiverController.router)
    client = TestClient(app)

    response = client.get("/receiver/")
    assert response.status_code == 200
    assert response.json() == {"message": "Receiver endpoint is working!"}


# ===================== /receiver/add_pix_key =====================


def test_add_pix_key_success(monkeypatch):
    fake_pix_helper = FakePixHelper()

    # no controller: from src.Helper.PixHelper import PixHelper as ph
    monkeypatch.setattr(
        "src.Controller.ReceiverController.ph",
        lambda: fake_pix_helper,
    )

    app = FastAPI()
    app.include_router(ReceiverController.router)

    # Usuário logado: receptor
    app.dependency_overrides[get_current_user_from_token] = (
        lambda: make_fake_user(10, "receptor")
    )

    client = TestClient(app)

    # ⚠️ usa os campos da PixModel
    payload = {
        "UserId": 10,
        "PixKey": "teste@pix.com",
        "KeyType": "email",
        # string vazia é aceita por Pydantic e cai no if not request.CreatedAt
        "CreatedAt": "",
    }

    response = client.post("/receiver/add_pix_key", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Pix key added"


def test_add_pix_key_forbidden_if_not_receiver(monkeypatch):
    fake_pix_helper = FakePixHelper()
    monkeypatch.setattr(
        "src.Controller.ReceiverController.ph",
        lambda: fake_pix_helper,
    )

    app = FastAPI()
    app.include_router(ReceiverController.router)

    # usuário NÃO é receptor
    app.dependency_overrides[get_current_user_from_token] = (
        lambda: make_fake_user(10, "doador")
    )

    client = TestClient(app)

    payload = {
        "UserId": 10,
        "PixKey": "teste@pix.com",
        "KeyType": "email",
        "CreatedAt": "",
    }

    response = client.post("/receiver/add_pix_key", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert (
        data["detail"]
        == "Unauthorized access: Only receivers can access this endpoint"
    )


# ===================== /receiver/delete_pix_key =====================


def test_delete_pix_key_success(monkeypatch):
    fake_pix_helper = FakePixHelper()
    monkeypatch.setattr(
        "src.Controller.ReceiverController.ph",
        lambda: fake_pix_helper,
    )

    app = FastAPI()
    app.include_router(ReceiverController.router)

    # Usuário logado: receptor
    app.dependency_overrides[get_current_user_from_token] = (
        lambda: make_fake_user(10, "receptor")
    )

    client = TestClient(app)

    # ⚠️ usa os campos da PixDeleteModel
    payload = {
        "UserId": 10,
        "PixId": 123,
    }

    response = client.request("DELETE", "/receiver/delete_pix_key", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Pix key deleted"


def test_delete_pix_key_forbidden_if_not_receiver(monkeypatch):
    fake_pix_helper = FakePixHelper()
    monkeypatch.setattr(
        "src.Controller.ReceiverController.ph",
        lambda: fake_pix_helper,
    )

    app = FastAPI()
    app.include_router(ReceiverController.router)

    # usuário NÃO é receptor
    app.dependency_overrides[get_current_user_from_token] = (
        lambda: make_fake_user(10, "doador")
    )

    client = TestClient(app)

    payload = {
        "UserId": 10,
        "PixId": 123,
    }

    response = client.request("DELETE", "/receiver/delete_pix_key", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert (
        data["detail"]
        == "Unauthorized access: Only receivers can access this endpoint"
    )


# ===================== /receiver/deactivate =====================


def test_deactivate_receiver_success(monkeypatch):
    cursor = FakeCursor()
    # SELECT retorna (ativo=True, tipo_usuario='receptor')
    cursor.to_fetch = [(True, "receptor")]
    connection = FakeConnection(cursor)

    class FakeConnectionHelper:
        def Connection(self):
            return connection

        def CloseConnection(self, conn):
            conn.closed = True

    monkeypatch.setattr(
        "src.Controller.ReceiverController.ConnectionHelper",
        FakeConnectionHelper,
    )

    app = FastAPI()
    app.include_router(ReceiverController.router)

    # usuário logado: receptor id 10
    app.dependency_overrides[get_current_user_from_token] = (
        lambda: make_fake_user(10, "receptor")
    )

    client = TestClient(app)

    # DeactivateModel: id_usuario
    payload = {"id_usuario": 10}

    response = client.post("/receiver/deactivate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Receiver with ID 10 deactivated successfully"
    assert connection.committed is True


def test_deactivate_receiver_forbidden_if_not_receiver_or_admin(monkeypatch):
    app = FastAPI()
    app.include_router(ReceiverController.router)

    # usuário logado: doador (tipo inválido)
    app.dependency_overrides[get_current_user_from_token] = (
        lambda: make_fake_user(10, "doador")
    )

    client = TestClient(app)

    payload = {"id_usuario": 10}

    response = client.post("/receiver/deactivate", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert (
        data["detail"]
        == "Unauthorized: Only receivers or admins can deactivate receivers"
    )


def test_deactivate_receiver_forbidden_if_trying_to_deactivate_other_user(monkeypatch):
    app = FastAPI()
    app.include_router(ReceiverController.router)

    # usuário logado: receptor id 10
    app.dependency_overrides[get_current_user_from_token] = (
        lambda: make_fake_user(10, "receptor")
    )

    client = TestClient(app)

    # tenta desativar outro usuário (99)
    payload = {"id_usuario": 99}

    response = client.post("/receiver/deactivate", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Unauthorized: You can only deactivate your own account"


def test_deactivate_receiver_user_not_found_or_inactive(monkeypatch):
    cursor = FakeCursor()
    cursor.to_fetch = [None]  # SELECT não encontrou usuário
    connection = FakeConnection(cursor)

    class FakeConnectionHelper:
        def Connection(self):
            return connection

        def CloseConnection(self, conn):
            conn.closed = True

    monkeypatch.setattr(
        "src.Controller.ReceiverController.ConnectionHelper",
        FakeConnectionHelper,
    )

    app = FastAPI()
    app.include_router(ReceiverController.router)

    # admin logado
    app.dependency_overrides[get_current_user_from_token] = (
        lambda: make_fake_user(1, "admin")
    )

    client = TestClient(app)

    payload = {"id_usuario": 99}

    response = client.post("/receiver/deactivate", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found or already inactive"
