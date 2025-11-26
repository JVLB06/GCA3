import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.Controller.ReceiverController import ReceiverController
from src.Helper.SecurityHelper import get_current_user_from_token

from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
import pytest
from typing import Callable, Any

from src.Controller.ReceiverController import ReceiverController
from src.Model.ProductModel import ProductModel

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



class MockUser:
    """Simula o objeto retornado por SignInHelper.GetKindOfUser."""
    def __init__(self, kind_of_user: str, user_id: int):
        self.KindOfUser = kind_of_user
        self.UserId = user_id



@pytest.fixture(scope="module") 
def app_client():
    """Cria e retorna o TestClient para a aplicação FastAPI."""
    app = FastAPI()
    app.include_router(ReceiverController.router)
    return TestClient(app)

@pytest.fixture
def product_data():
    """Dados de produto válidos para a criação/atualização."""
    return {
        "name": "Bola de Futebol",
        "description": "Bola para doação",
        "value": 120.00
    }

def create_mock_get_kind_of_user(user_type: str, user_id: int) -> Callable[[Any], MockUser]:
   
    def mock_func(user_email: str) -> MockUser:
        return MockUser(kind_of_user=user_type, user_id=user_id)
    return mock_func

def test_get_product_details_success(app_client, mocker):

    mock_product = ProductModel(
        productId=5, causeId=42, name="Caneta", description="Caneta azul", value=2.50
    )
    
    mocker.patch(
        'src.Controller.ReceiverController.ProductHelper.get_product_by_id',
        return_value=mock_product
    )
    
    response = app_client.get("/receiver/product/5")
    
    assert response.status_code == 200
    assert response.json()['name'] == "Caneta"
    assert float(response.json()['value']) == 2.50 


def test_post_create_product_success(app_client, mocker, product_data, monkeypatch):
 
    mock_receptor_func = create_mock_get_kind_of_user(user_type='receptor', user_id=42)
    monkeypatch.setattr(
        'src.Controller.ReceiverController.SignInHelper.GetKindOfUser',
        mock_receptor_func
    )
    
    mock_create = mocker.patch(
        'src.Controller.ReceiverController.ProductHelper.create_product',
        return_value=15
    )
    
    app_client.app.dependency_overrides[get_current_user_from_token] = lambda: 'test@example.com'
    
    response = app_client.post("/receiver/create_product", json=product_data)

    app_client.app.dependency_overrides = {} 

    assert response.status_code == 200
    assert response.json()['productId'] == 15
    
    # Verifica se o ID de segurança (causeId) foi injetado corretamente (42)
    product_model_sent = mock_create.call_args[0][0]
    assert product_model_sent.causeId == 42


def test_post_create_product_unauthorized(app_client, mocker, product_data, monkeypatch):

    # 1. SUBSTITUIÇÃO CHAVE: Mocka o SigninHelper para autenticação como 'doador'
    mock_doador_func = create_mock_get_kind_of_user(user_type='doador', user_id=10)
    monkeypatch.setattr(
        'src.Controller.ReceiverController.SignInHelper.GetKindOfUser',
        mock_doador_func
    )

    # 2. Mocka a Dependência de Token
    app_client.app.dependency_overrides[get_current_user_from_token] = lambda: 'doador@example.com'
    
    response = app_client.post("/receiver/create_product", json=product_data)
    
    app_client.app.dependency_overrides = {} 
    
    assert response.status_code == 403
    assert "Only receivers can create products" in response.json()['detail']


def test_put_update_product_success(app_client, mocker, monkeypatch):
    
    update_data = {
        "productId": 5, 
        "name": "Updated Item", 
        "description": "Nova Descrição", 
        "value": 50.00
    }
    
    # 1. SUBSTITUIÇÃO CHAVE: Mock Auth como 'receptor'
    mock_receptor_func = create_mock_get_kind_of_user(user_type='receptor', user_id=42)
    monkeypatch.setattr(
        'src.Controller.ReceiverController.SignInHelper.GetKindOfUser',
        mock_receptor_func
    )
    
    # 2. Mock Helper para simular sucesso
    mock_update = mocker.patch(
        'src.Controller.ReceiverController.ProductHelper.update_product',
        return_value=True
    )
    
    # 3. Mock Token Dependency
    app_client.app.dependency_overrides[get_current_user_from_token] = lambda: 'test@example.com'
    
    response = app_client.put("/receiver/update_product", json=update_data)
    
    app_client.app.dependency_overrides = {} 

    assert response.status_code == 200
    assert response.json() == {"message": "Product updated successfully"}
    
    # Verifica se o ID de segurança (causeId) foi injetado corretamente (42)
    product_model_sent = mock_update.call_args[0][0]
    assert product_model_sent.causeId == 42


def test_put_update_product_unauthorized_role(app_client, mocker, monkeypatch):
  
    update_data = {
        "productId": 5, 
        "name": "Updated Item", 
        "description": "Desc", 
        "value": 50.00
    }
    
    mock_doador_func = create_mock_get_kind_of_user(user_type='doador', user_id=10)
    monkeypatch.setattr(
        'src.Controller.ReceiverController.SignInHelper.GetKindOfUser',
        mock_doador_func
    )
    
    app_client.app.dependency_overrides[get_current_user_from_token] = lambda: 'doador@example.com'
    
    response = app_client.put("/receiver/update_product", json=update_data)
    
    app_client.app.dependency_overrides = {} 
    
    assert response.status_code == 403
    assert "Only receivers can update products" in response.json()['detail']
