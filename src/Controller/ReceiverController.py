from fastapi import APIRouter, Depends
from datetime import datetime
from src.Model.PixModel import PixModel
from src.Model.PixDeleteModel import PixDeleteModel
from src.Helper.PixHelper import PixHelper as ph
from src.Helper.SecurityHelper import get_current_user_from_token

class ReceiverController:
    
    router = APIRouter(prefix="/receiver", tags=["Receiver"])

    @router.get("/")
    async def get_receiver():
        return {"message": "Receiver endpoint is working!"}
    
    @router.post("/add_pix_key")
    async def add_pix_key(request: PixModel,
        user: str = Depends(get_current_user_from_token)):
        if not request.CreatedAt:
            request.CreatedAt = datetime.now().isoformat()

        return {"message": ph().add_pix_key(request)}
    
    @router.delete("/delete_pix_key")
    async def delete_pix_key(request: PixDeleteModel,
        user: str = Depends(get_current_user_from_token)):
        return {"message": ph().delete_pix_key(request)}