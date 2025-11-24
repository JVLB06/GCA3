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

    # endpoint exige user == "recebedor"
    app.dependency_overrides[get_current_user_from_token] = lambda: "recebedor"

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
    # usuário NÃO é recebedor
    app.dependency_overrides[get_current_user_from_token] = lambda: "doador"

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
    app.dependency_overrides[get_current_user_from_token] = lambda: "recebedor"

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
    app.dependency_overrides[get_current_user_from_token] = lambda: "doador"

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
    # usuário logado: receptor id 10
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return FakeUserData(user_id=10, kind_of_user="receptor")

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
        "src.Controller.ReceiverController.SignInHelper",
        FakeSignInHelper,
    )
    monkeypatch.setattr(
        "src.Controller.ReceiverController.ConnectionHelper",
        FakeConnectionHelper,
    )

    app = FastAPI()
    app.include_router(ReceiverController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "receiver@example.com"

    client = TestClient(app)

    # DeactivateModel: id_usuario (mesmo padrão que vc já usa pros outros)
    payload = {"id_usuario": 10}

    response = client.post("/receiver/deactivate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Receiver with ID 10 deactivated successfully"
    assert connection.committed is True


def test_deactivate_receiver_forbidden_if_not_receiver_or_admin(monkeypatch):
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return FakeUserData(user_id=10, kind_of_user="doador")  # tipo inválido

    monkeypatch.setattr(
        "src.Controller.ReceiverController.SignInHelper",
        FakeSignInHelper,
    )

    app = FastAPI()
    app.include_router(ReceiverController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "user@example.com"

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
    # usuário logado: receptor id 10, tentando desativar 99
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return FakeUserData(user_id=10, kind_of_user="receptor")

    monkeypatch.setattr(
        "src.Controller.ReceiverController.SignInHelper",
        FakeSignInHelper,
    )

    app = FastAPI()
    app.include_router(ReceiverController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "user@example.com"

    client = TestClient(app)

    payload = {"id_usuario": 99}

    response = client.post("/receiver/deactivate", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Unauthorized: You can only deactivate your own account"


def test_deactivate_receiver_user_not_found_or_inactive(monkeypatch):
    # admin logado, mas usuário não existe / já inativo
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return FakeUserData(user_id=1, kind_of_user="admin")

    cursor = FakeCursor()
    cursor.to_fetch = [None]  # SELECT não encontrou usuário
    connection = FakeConnection(cursor)

    class FakeConnectionHelper:
        def Connection(self):
            return connection

        def CloseConnection(self, conn):
            conn.closed = True

    monkeypatch.setattr(
        "src.Controller.ReceiverController.SignInHelper",
        FakeSignInHelper,
    )
    monkeypatch.setattr(
        "src.Controller.ReceiverController.ConnectionHelper",
        FakeConnectionHelper,
    )

    app = FastAPI()
    app.include_router(ReceiverController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "admin@example.com"

    client = TestClient(app)

    payload = {"id_usuario": 99}

    response = client.post("/receiver/deactivate", json=payload)

    # ⚠️ Se o seu controller ainda estiver com `except Exception` engolindo HTTPException,
    # isso pode retornar 500. O ideal é ter:
    #   except HTTPException: raise
    #   except Exception as e: ...
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found or already inactive"
