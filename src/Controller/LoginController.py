from fastapi import APIRouter, HTTPException, Request
from Model import CadastrateModel, LoginModel
from Helper.SignInHelper import SignInHelper

router = APIRouter()

class LoginController:
    @router.post("/cadastrate")
    async def cadastrate(request: CadastrateModel.CadastrateModel):
        if request.IsReceiver:
            if SignInHelper().Cadastrate(request):
                return {"message": "Receiver login successful", "user": request.Name}
            else:
                raise HTTPException(status_code=400, detail="Cadastration failed")
        else:
            request.Cause = None
            request.Document = None
            if SignInHelper().Cadastrate(request):
                return {"message": "Donor login successful", "user": request.Name}
            else: 
                raise HTTPException(status_code=400, detail="Cadastration failed")
    
    @router.get("/login")
    async def login(request: LoginModel.LoginModel):
        if SignInHelper().SignIn(request):
            return {"message": "Login successful", "user": request.username}
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")