from fastapi import APIRouter, HTTPException, Request
from src.Model import CadastrateModel, LoginModel
from src.Helper.SignInHelper import SignInHelper
from src.Helper.TokenHelper import TokenHelper

class ReceiverController:
    
    router = APIRouter(prefix="/receiver", tags=["Receiver"])

    @router.get("/")
    async def get_receiver():
        return {"message": "Receiver endpoint is working!"}