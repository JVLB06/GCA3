from fastapi import APIRouter, HTTPException, Request
from src.Model import CadastrateModel, LoginModel
from src.Helper.SignInHelper import SignInHelper
from src.Helper.TokenHelper import TokenHelper

class LoginController:

    router = APIRouter()

    @router.post("/cadastrate")
    async def cadastrate(request: CadastrateModel.CadastrateModel):
        if request.IsReceiver == "receptor":
            if SignInHelper().ValidateAddress(request.Address) == False:
                raise HTTPException(status_code=400, detail="Invalid Address")
            elif SignInHelper().Cadastrate(request):
                return {"message": "Receiver login successful", "user": request.Name}
            else:
                raise HTTPException(status_code=400, detail="Cadastration failed")
        elif request.IsReceiver == "doador" or request.IsReceiver == "admin":
            request.Cause = None
            request.Document = None
            request.Address = None
            if SignInHelper().Cadastrate(request):
                return {"message": "Donor login successful", "user": request.Name}
            else: 
                raise HTTPException(status_code=400, detail="Cadastration failed")
        else:
            raise HTTPException(status_code=400, detail="Cadastration failed User is not valid")
    
    @router.post("/login")
    async def login(request: LoginModel.LoginModel):
        if SignInHelper().SignIn(request):
            # Gera token após login bem-sucedido
            UserInfo = SignInHelper().GetKindOfUser(str(request.Username))
            if not UserInfo:
                raise HTTPException(status_code=404, detail="Error retrieving user type")
            # Correção: Usar o email (request.Username) como 'sub' em vez de UserInfo.KindOfUser
            access_token = TokenHelper().create_access_token(data={"sub": request.Username})
            return {"message": "Login successful", "user": request.Username, "access_token": access_token, "token_type": "bearer"}
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
