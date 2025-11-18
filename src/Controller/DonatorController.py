from fastapi import APIRouter, HTTPException, Request
from src.Model import CadastrateModel, LoginModel
from src.Helper.SignInHelper import SignInHelper
from src.Helper.TokenHelper import TokenHelper

class DonatorController:
    
    router = APIRouter(prefix="/donator", tags=["Donator"])

    @router.get("/")
    async def get_donator():
        return {"message": "Donator endpoint is working!"}
