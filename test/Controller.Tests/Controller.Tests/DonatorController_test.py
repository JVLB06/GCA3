import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.Controller.DonatorController import DonatorController
from src.Helper.SecurityHelper import get_current_user_from_token

class FakeUserData:
    def __init__(self, user_id: int, kind_of_user: str):
        self.UserId = user_id
        self.KindOfUser = kind_of_user


class FakeCursor:
    def __init__(self):
        self.to_fetch = []
        self.executed = []

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

def test_get_donator_root():
    app = FastAPI()
    app.include_router(DonatorController.router)
    client = TestClient(app)

    response = client.get("/donator/")
    assert response.status_code == 200
    assert response.json() == {"message": "Donator endpoint is working!"}

class FakeReceiversHelper:
    def get_receivers(self, type_of_order: str):
        return [{"id": 1, "name": "Receiver 1", "type": type_of_order}]

    def validate_cause_id(self, cause_id: int) -> bool:
        return True  # usado em /favorite; aqui não faz diferença


def test_list_receivers_success(monkeypatch):
    # Mocka ReceiversHelper
    monkeypatch.setattr(
        "src.Controller.DonatorController.ReceiversHelper",
        lambda: FakeReceiversHelper(),
    )

    app = FastAPI()
    app.include_router(DonatorController.router)

    # Usuário logado será um "doador"
    app.dependency_overrides[get_current_user_from_token] = lambda: "doador"

    client = TestClient(app)

    response = client.get("/donator/list_receivers/food")
    assert response.status_code == 200
    data = response.json()
    assert "receivers" in data
    assert len(data["receivers"]) == 1
    assert data["receivers"][0]["type"] == "food"


def test_list_receivers_forbidden_if_not_donator(monkeypatch):
    # Não precisamos mockar ReceiversHelper aqui, pois a validação falha antes
    app = FastAPI()
    app.include_router(DonatorController.router)

    # Usuário logado NÃO é doador
    app.dependency_overrides[get_current_user_from_token] = lambda: "admin"

    client = TestClient(app)

    response = client.get("/donator/list_receivers/food")
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Unauthorized access: Only donators can access this endpoint"


# ========== TESTES DO /donator/deactivate ==========


def test_deactivate_donator_success(monkeypatch):
    # Fake SignInHelper -> sempre retorna doador com id 10
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return FakeUserData(user_id=10, kind_of_user="doador")

    # Fake ConnectionHelper -> retorna uma conexão com cursor configurado
    cursor = FakeCursor()
    # fetchone() irá retornar (ativo=True, tipo_usuario='doador')
    cursor.to_fetch = [(True, "doador")]
    connection = FakeConnection(cursor)

    class FakeConnectionHelper:
        def Connection(self):
            return connection

        def CloseConnection(self, conn):
            conn.closed = True

    monkeypatch.setattr(
        "src.Controller.DonatorController.SignInHelper",
        FakeSignInHelper,
    )
    monkeypatch.setattr(
        "src.Controller.DonatorController.ConnectionHelper",
        FakeConnectionHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)

    # Email do usuário logado (token) – o valor em si não importa para o fake
    app.dependency_overrides[get_current_user_from_token] = lambda: "user@example.com"

    client = TestClient(app)

    payload = {"id_usuario": 10}

    response = client.post("/donator/deactivate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Donator with ID 10 deactivated successfully"
    assert connection.committed is True


def test_deactivate_donator_forbidden_if_not_donator_or_admin(monkeypatch):
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return FakeUserData(user_id=10, kind_of_user="receptor")  # tipo inválido

    monkeypatch.setattr(
        "src.Controller.DonatorController.SignInHelper",
        FakeSignInHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "user@example.com"

    client = TestClient(app)

    payload = {"id_usuario": 10}

    response = client.post("/donator/deactivate", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert (
        data["detail"]
        == "Unauthorized: Only donators or admins can deactivate donators"
    )


def test_deactivate_donator_forbidden_if_trying_to_deactivate_other_user(monkeypatch):
    # Usuário logado é doador, mas com outro id
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return FakeUserData(user_id=10, kind_of_user="doador")

    monkeypatch.setattr(
        "src.Controller.DonatorController.SignInHelper",
        FakeSignInHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "user@example.com"

    client = TestClient(app)

    # Tenta inativar id 99, mas o usuário logado é 10
    payload = {"id_usuario": 99}

    response = client.post("/donator/deactivate", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Unauthorized: You can only deactivate your own account"


def test_deactivate_donator_user_not_found(monkeypatch):
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return FakeUserData(user_id=10, kind_of_user="admin")

    # Aqui o admin pode desativar qualquer um, mas o usuário não existe / já inativo
    cursor = FakeCursor()
    cursor.to_fetch = [None]  # SELECT não encontrou nada
    connection = FakeConnection(cursor)

    class FakeConnectionHelper:
        def Connection(self):
            return connection

        def CloseConnection(self, conn):
            conn.closed = True

    monkeypatch.setattr(
        "src.Controller.DonatorController.SignInHelper",
        FakeSignInHelper,
    )
    monkeypatch.setattr(
        "src.Controller.DonatorController.ConnectionHelper",
        FakeConnectionHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "admin@example.com"

    client = TestClient(app)

    payload = {"id_usuario": 99}

    response = client.post("/donator/deactivate", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found or already inactive"


# ========== TESTES DO /donator/favorite/{cause_id} ==========


def test_favorite_cause_success(monkeypatch):
    # Fake para usuário doador
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return FakeUserData(user_id=10, kind_of_user="doador")

    # Fake para ReceiversHelper validando a causa
    class FakeReceiversHelper:
        def validate_cause_id(self, cause_id: int) -> bool:
            return True

    # Fake para FavoriteHelper simulando sucesso
    class FakeFavoriteHelper:
        def add_favorite(self, fav_info):
            # Garante que o controller está montando corretamente o modelo
            assert fav_info.CauseId == 123
            assert fav_info.UserId == 10
            return {"message": f"Cause with ID {fav_info.CauseId} favorited successfully"}

    monkeypatch.setattr(
        "src.Controller.DonatorController.SignInHelper",
        FakeSignInHelper,
    )
    monkeypatch.setattr(
        "src.Controller.DonatorController.ReceiversHelper",
        lambda: FakeReceiversHelper(),
    )
    monkeypatch.setattr(
        "src.Controller.DonatorController.FavoriteHelper",
        FakeFavoriteHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "user@example.com"

    client = TestClient(app)

    response = client.post("/donator/favorite/123")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Cause with ID 123 favorited successfully"


def test_favorite_cause_forbidden_if_not_donator(monkeypatch):
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            # Usuário não é doador
            return FakeUserData(user_id=10, kind_of_user="admin")

    # Não precisamos mockar ReceiversHelper/FavoriteHelper aqui,
    # pois o fluxo deve barrar antes.
    monkeypatch.setattr(
        "src.Controller.DonatorController.SignInHelper",
        FakeSignInHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "admin@example.com"

    client = TestClient(app)

    response = client.post("/donator/favorite/123")
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Unauthorized: Only donators can favorite causes"


def test_favorite_cause_not_found_if_invalid_cause(monkeypatch):
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return FakeUserData(user_id=10, kind_of_user="doador")

    class FakeReceiversHelperInvalid:
        def validate_cause_id(self, cause_id: int) -> bool:
            return False  # causa inválida / inativa

    monkeypatch.setattr(
        "src.Controller.DonatorController.SignInHelper",
        FakeSignInHelper,
    )
    monkeypatch.setattr(
        "src.Controller.DonatorController.ReceiversHelper",
        lambda: FakeReceiversHelperInvalid(),
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "user@example.com"

    client = TestClient(app)

    response = client.post("/donator/favorite/123")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Cause not found or not active"


def test_favorite_cause_conflict_if_already_favorited(monkeypatch):
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return FakeUserData(user_id=10, kind_of_user="doador")

    class FakeReceiversHelperOK:
        def validate_cause_id(self, cause_id: int) -> bool:
            return True

    # Fake FavoriteHelper que simula conflito (já favoritado)
    class FakeFavoriteHelper:
        def add_favorite(self, fav_info):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=409,
                detail="Cause already favorited",
            )

    monkeypatch.setattr(
        "src.Controller.DonatorController.SignInHelper",
        FakeSignInHelper,
    )
    monkeypatch.setattr(
        "src.Controller.DonatorController.ReceiversHelper",
        lambda: FakeReceiversHelperOK(),
    )
    monkeypatch.setattr(
        "src.Controller.DonatorController.FavoriteHelper",
        FakeFavoriteHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "user@example.com"

    client = TestClient(app)

    response = client.post("/donator/favorite/123")
    assert response.status_code == 409
    data = response.json()
    assert data["detail"] == "Cause already favorited"

def test_remove_favorite_success(monkeypatch):
    # Aqui o controller compara diretamente com string "doador",
    # então o fake precisa retornar uma string, não um objeto.
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return "doador"

    class FakeFavoriteHelper:
        def remove_favorite(self, fav_id: int):
            assert fav_id == 1
            return {"message": "Favorite removed successfully"}

    monkeypatch.setattr(
        "src.Controller.DonatorController.SignInHelper",
        FakeSignInHelper,
    )
    monkeypatch.setattr(
        "src.Controller.DonatorController.FavoriteHelper",
        FakeFavoriteHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "user@example.com"

    client = TestClient(app)

    response = client.delete("/donator/favorite/1")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Favorite removed successfully"


def test_remove_favorite_forbidden_if_not_donator(monkeypatch):
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return "admin"  # qualquer coisa diferente de "doador"

    monkeypatch.setattr(
        "src.Controller.DonatorController.SignInHelper",
        FakeSignInHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "admin@example.com"

    client = TestClient(app)

    response = client.delete("/donator/favorite/1")
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Unauthorized: Only donators can remove favorites"

def test_list_favorites_success(monkeypatch):
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            # Aqui o controller espera um objeto com UserId e KindOfUser
            return FakeUserData(user_id=10, kind_of_user="doador")

    class FakeFavoriteHelper:
        def list_favorites(self, user_id: int):
            assert user_id == 10
            return [
                {"id": 1, "cause_id": 123},
                {"id": 2, "cause_id": 456},
            ]

    monkeypatch.setattr(
        "src.Controller.DonatorController.SignInHelper",
        FakeSignInHelper,
    )
    monkeypatch.setattr(
        "src.Controller.DonatorController.FavoriteHelper",
        FakeFavoriteHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "user@example.com"

    client = TestClient(app)

    response = client.get("/donator/favorites")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["cause_id"] == 123
    assert data[1]["cause_id"] == 456


def test_list_favorites_forbidden_if_not_donator(monkeypatch):
    class FakeSignInHelper:
        def GetKindOfUser(self, email: str):
            return FakeUserData(user_id=10, kind_of_user="admin")

    monkeypatch.setattr(
        "src.Controller.DonatorController.SignInHelper",
        FakeSignInHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: "admin@example.com"

    client = TestClient(app)

    response = client.get("/donator/favorites")
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Unauthorized: Only donators can view favorites"


def test_get_cause_products_success(monkeypatch):
    class FakeProductHelper:
        def list_products(self, UserId: int = None):
            # aqui o controller passa causeId como argumento para list_products
            assert UserId == 10
            return [
                {
                    "ProductId": 1,
                    "CauseId": 10,
                    "ProductName": "Cesta Básica",
                    "Description": "Cesta com alimentos",
                    "Value": 100.0,
                },
                {
                    "ProductId": 2,
                    "CauseId": 10,
                    "ProductName": "Roupa",
                    "Description": "Kit de roupas",
                    "Value": 150.0,
                },
            ]

    # Monkeypatch da ProductHelper usada no DonatorController
    monkeypatch.setattr(
        "src.Controller.DonatorController.ProductHelper",
        FakeProductHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    # usuário logado é doador
    app.dependency_overrides[get_current_user_from_token] = lambda: "doador"

    client = TestClient(app)

    response = client.get("/donator/get_cause_products/10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["CauseId"] == 10
    assert data[1]["CauseId"] == 10

def test_get_cause_products_forbidden_if_not_donator(monkeypatch):
    class FakeProductHelper:
        def list_products(self, UserId: int = None):
            pytest.fail("Não deveria chamar ProductHelper se usuário não é doador")

    monkeypatch.setattr(
        "src.Controller.DonatorController.ProductHelper",
        FakeProductHelper,
    )

    app = FastAPI()
    app.include_router(DonatorController.router)
    # usuário NÃO é doador
    app.dependency_overrides[get_current_user_from_token] = lambda: "receptor"

    client = TestClient(app)

    response = client.get("/donator/get_cause_products/10")
    assert response.status_code == 403
    data = response.json()
    assert (
        data["detail"]
        == "Unauthorized: Only donators can view products by cause"
    )
