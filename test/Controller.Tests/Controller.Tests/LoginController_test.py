import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.Controller.LoginController import LoginController

class FakeSignInHelper:
    def __init__(self):
        pass

    def ValidateAddress(self, address: str) -> bool:
        return True

    def Cadastrate(self, request) -> bool:
        return True

    def SignIn(self, request) -> bool:
        return True

    def GetKindOfUser(self, username: str):
        return {"KindOfUser": "receptor"}

class FakeTokenHelper:
    def create_access_token(self, data: dict) -> str:
        return "fake-token"

@pytest.fixture
def client(monkeypatch):
    # Troca os helpers reais pelos fakes
    monkeypatch.setattr(
        "src.Controller.LoginController.SignInHelper",
        FakeSignInHelper,
    )
    monkeypatch.setattr(
        "src.Controller.LoginController.TokenHelper",
        FakeTokenHelper,
    )

    # Cria um app FastAPI só para os testes
    app = FastAPI()
    app.include_router(LoginController.router)

    return TestClient(app)

def test_CadastrateUserWithSucces(client):

    payload = {
        "Email" : "teste@gmail.com",
        "Password" : "12345",
        "IsReceiver" : "receptor",
        "Document" : "12123123000115",
        "Name" : "Ajude as pessoas",
        "Cause" : "Vamos ajudar as pessoas",
        "Address" : "85123000"
    }

    response = client.post("/cadastrate", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["message"] == "Receiver login successful"
    assert data["user"] == "Ajude as pessoas"

def test_CadastrateUserReturnErrorIfInvalidData(client):

    payload = {
        "Email" : "teste@gmail.com",
        "Password" : "12345",
        "IsReceiver" : "usuario",
        "Document" : "12123123000115",
        "Name" : "Ajude as pessoas",
        "Cause" : "Vamos ajudar as pessoas",
        "Address" : "85123000"
    }

    response = client.post("/cadastrate", json=payload)

    assert response.status_code == 400
    data = response.json()

    assert "Cadastration failed" in data["detail"]

def test_LoginWithSucces(client):

    payload = {
        "Username" : "teste@gmail.com",
        "Password" : "12345"
    }

    response = client.post("/login", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["message"] == "Login successful"

def test_LoginReturnErrorIfInvalidCredentials(monkeypatch):

    class FakeSignInHelperInvalid:
        def __init__(self):
            pass

        def ValidateAddress(self, address: str) -> bool:
            return True

        def Cadastrate(self, request) -> bool:
            return True

        def SignIn(self, request) -> bool:
            # Sempre falha o login
            return False

        def GetKindOfUser(self, username: str):
            return {"KindOfUser": "receptor"}

    # Mocka os helpers SÓ para esse teste
    monkeypatch.setattr(
        "src.Controller.LoginController.SignInHelper",
        FakeSignInHelperInvalid,
    )
    monkeypatch.setattr(
        "src.Controller.LoginController.TokenHelper",
        FakeTokenHelper,
    )

    app = FastAPI()
    app.include_router(LoginController.router)
    client = TestClient(app)


    payload = {
        "Username" : "teste@gmail.com",
        "Password" : "wrongpassword"
    }

    response = client.post("/login", json=payload)

    assert response.status_code == 401
    data = response.json()

    assert "Invalid credentials" in data["detail"]