from fastapi import APIRouter, HTTPException, Request, Depends
from src.Model.ListReceiversRequestModel import ListReceiversRequestModel
from src.Helper.ReceiversHelper import ReceiversHelper
from src.Helper.SecurityHelper import get_current_user_from_token

class DonatorController:
    
    router = APIRouter(prefix="/donator", tags=["Donator"])

    @router.get("/")
    async def get_donator():
        return {"message": "Donator endpoint is working!"}
    
    @router.post("list_receivers")
    async def list_receivers(request: ListReceiversRequestModel,
        user: str = Depends(get_current_user_from_token)):

        if user != "doador":
            raise HTTPException(status_code=403, detail="Unauthorized access: Only donators can access this endpoint")
        try:
            helper = ReceiversHelper()
            receivers = helper.get_receivers(request)
            return {"receivers": receivers}
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Error fetching receivers: {e}")