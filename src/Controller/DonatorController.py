from fastapi import APIRouter, HTTPException, Depends
from src.Model.DeactivateModel import DeactivateModel 
from src.Model.AddFavoriteModel import AddFavoriteModel 
from src.Model.DonationModel import DonationModel
from src.Helper.DonationsHelper import DonationsHelper
from src.Helper.ReceiversHelper import ReceiversHelper
from src.Helper.SecurityHelper import get_current_user_from_token
from src.Helper.ConnectionHelper import ConnectionHelper 
from src.Helper.SignInHelper import SignInHelper
from src.Model.TokenModel import TokenModel
from src.Helper.ProductHelper import ProductHelper
from src.Helper.FavoritesHelper import FavoriteHelper  

class DonatorController:
    
    router = APIRouter(prefix="/donator", tags=["Donator"])

    @router.get("/")
    async def get_donator():
        return {"message": "Donator endpoint is working!"}
    
    @router.get("/list_receivers/{TypeOfOrder}")
    async def list_receivers(TypeOfOrder: str, user: TokenModel = Depends(get_current_user_from_token)):
        
        if user.KindOfUser != "doador":
            raise HTTPException(status_code=403, detail="Unauthorized access: Only donators can access this endpoint")
        try:
            helper = ReceiversHelper()
            receivers = helper.get_receivers(TypeOfOrder)
            return {"receivers": receivers}
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Error fetching receivers: {e}")

    @router.post("/deactivate")
    async def deactivate_donator(request: DeactivateModel, user: TokenModel = Depends(get_current_user_from_token)):
        # Verificar se é doador ou admin
        if user.KindOfUser not in ['doador', 'admin']:
            raise HTTPException(status_code=403, detail="Unauthorized: Only donators or admins can deactivate donators")

        # Se não for admin, só pode inativar si mesmo
        if user.KindOfUser != 'admin' and request.id_usuario != user.UserId:
            raise HTTPException(status_code=403, detail="Unauthorized: You can only deactivate your own account")

        # Conectar ao banco e validar/inativar
        conn_helper = ConnectionHelper()
        connection = conn_helper.Connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")

        try:
            cursor = connection.cursor()
            cursor.execute("SELECT ativo, tipo_usuario FROM usuarios WHERE id_usuario = %s", (request.id_usuario,))
            result = cursor.fetchone()
            if not result or not result[0]:  # Não encontrado ou já inativo
                raise HTTPException(status_code=404, detail="User not found or already inactive")
            if result[1] != 'doador':  # Garantir que é um doador
                raise HTTPException(status_code=403, detail="Unauthorized: Can only deactivate donators")

            # UPDATE: Inativar
            cursor.execute("UPDATE usuarios SET ativo = false WHERE id_usuario = %s", (request.id_usuario,))
            connection.commit()
            return {"message": f"Donator with ID {request.id_usuario} deactivated successfully"}
        except HTTPException:
            raise
        except Exception as e:
            connection.rollback()
            raise HTTPException(status_code=500, detail=f"Error deactivating donator: {e}")
        finally:
            conn_helper.CloseConnection(connection)

    @router.post("/favorite/{cause_id}")
    async def favorite_cause(cause_id: int, user: TokenModel = Depends(get_current_user_from_token)):
        if user.KindOfUser != 'doador':
            raise HTTPException(status_code=403, detail="Unauthorized: Only donators can favorite causes")

        receivers_helper = ReceiversHelper()
        if not receivers_helper.validate_cause_id(cause_id):
            raise HTTPException(status_code=404, detail="Cause not found or not active")

        fav_info = AddFavoriteModel(CauseId=cause_id, UserId=user.UserId)

        return FavoriteHelper().add_favorite(fav_info)

    @router.delete("/favorite/{fav_id}")
    async def remove_favorite(fav_id: int, user: TokenModel = Depends(get_current_user_from_token)):
        if user.KindOfUser != "doador":
            raise HTTPException(status_code=403, detail="Unauthorized: Only donators can remove favorites")
        
        return FavoriteHelper().remove_favorite(fav_id)
    
    @router.get("/favorites")
    async def list_favorites(user: TokenModel = Depends(get_current_user_from_token)):
        if user.KindOfUser != 'doador':
            raise HTTPException(status_code=403, detail="Unauthorized: Only donators can view favorites")

        return FavoriteHelper().list_favorites(user.UserId)
    
    @router.post("/add_donation")
    async def add_donation(donation_info: DonationModel, user: TokenModel = Depends(get_current_user_from_token)):
        if user.KindOfUser != 'doador':
            raise HTTPException(status_code=403, detail="Unauthorized: Only donators can add donations")

        donation_info.DonorId = user.UserId

        donations_helper = DonationsHelper()
        return donations_helper.add_donations(donation_info)
    
    @router.get("/list_donations_made")
    async def list_donations(user: TokenModel = Depends(get_current_user_from_token)):
        if user.KindOfUser != "doador":
            raise HTTPException(status_code=403, detail="Unauthorized: Only donators can list donations made")
        
        return DonationsHelper().list_donations_by_user(user.UserId)

    @router.get("/get_cause_products/{causeId}")
    async def get_cause_products(causeId: int, user: TokenModel = Depends(get_current_user_from_token)):
        if user.KindOfUser != "doador":
            raise HTTPException(status_code=403, detail="Unauthorized: Only donators can view products by cause")      

        return ProductHelper().list_products(causeId)
