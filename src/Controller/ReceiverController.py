from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from src.Model.PixModel import PixModel
from src.Model.PixDeleteModel import PixDeleteModel
from src.Model.DeactivateModel import DeactivateModel  
from src.Helper.DonationsHelper import DonationsHelper
from src.Model.DeleteProductModel import DeleteProductModel
from src.Model.ListProductModel import ListProductModel 
from src.Helper.PixHelper import PixHelper as ph
from src.Helper.SecurityHelper import get_current_user_from_token
from src.Helper.ConnectionHelper import ConnectionHelper  
from src.Helper.SignInHelper import SignInHelper  
from src.Model.TokenModel import TokenModel
from src.Model.ProductModel import ProductModel
from src.Helper.ProductHelper import ProductHelper

class ReceiverController:
    
    router = APIRouter(prefix="/receiver", tags=["Receiver"])

    @router.get("/")
    async def get_receiver():
        return {"message": "Receiver endpoint is working!"}
    
    @router.post("/add_pix_key")
    async def add_pix_key(request: PixModel,
        user: TokenModel = Depends(get_current_user_from_token)):
        
        if user.KindOfUser != "receptor":
            raise HTTPException(status_code=403, detail="Unauthorized access: Only receivers can access this endpoint")
        
        request.UserId = user.UserId

        if not request.CreatedAt:
            request.CreatedAt = datetime.now().isoformat()

        return {"message": ph().add_pix_key(request)}
    
    @router.delete("/delete_pix_key")
    async def delete_pix_key(request: PixDeleteModel,
        user: TokenModel = Depends(get_current_user_from_token)):

        if user.KindOfUser != "receptor":
            raise HTTPException(status_code=403, detail="Unauthorized access: Only receivers can access this endpoint")
        
        request.UserId = user.UserId

        return {"message": ph().delete_pix_key(request)}

    # Novo endpoint para inativação de receptor
    @router.post("/deactivate")
    async def deactivate_receiver(request: DeactivateModel, user: TokenModel = Depends(get_current_user_from_token)):
        if user.KindOfUser not in ['receptor', 'admin']:  # Nota: assumindo 'receptor' como 'receptor' no enum
            raise HTTPException(status_code=403, detail="Unauthorized: Only receivers or admins can deactivate receivers")

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
            # SELECT: Verificar se o ID existe e está ativo
            cursor.execute("SELECT ativo, tipo_usuario FROM usuarios WHERE id_usuario = %s", (request.id_usuario,))
            result = cursor.fetchone()
            if not result or not result[0]:  # Não encontrado ou já inativo
                raise HTTPException(status_code=404, detail="User not found or already inactive")
            if result[1] != 'receptor':  # Garantir que é um receptor
                raise HTTPException(status_code=403, detail="Unauthorized: Can only deactivate receivers")

            # UPDATE: Inativar
            cursor.execute("UPDATE usuarios SET ativo = false WHERE id_usuario = %s", (request.id_usuario,))
            connection.commit()
            return {"message": f"Receiver with ID {request.id_usuario} deactivated successfully"}
        except HTTPException:
            raise
        except Exception as e:
            connection.rollback()
            raise HTTPException(status_code=500, detail=f"Error deactivating receiver: {e}")
        finally:
            conn_helper.CloseConnection(connection)

    @router.get("/list_donations_received")
    async def list_donations_received(user: TokenModel = Depends(get_current_user_from_token)):
        if user.KindOfUser != 'receptor':
            raise HTTPException(status_code=403, detail="Unauthorized: Only receivers can access this endpoint")

        try:
            donations_helper = DonationsHelper()
            donations = donations_helper.list_donations_received(user.UserId)
            return {"donations": donations}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching donations: {e}")

    @router.post("/create_product")
    async def create_product(request: ProductModel, user: TokenModel = Depends(get_current_user_from_token)):
        
        request.CauseId = user.UserId
        
        if user.KindOfUser != "receptor":
             raise HTTPException(status_code=403, detail="Unauthorized access: Only receivers can create products")

        helper = ProductHelper()
        new_id = helper.create_product(request)

        if new_id:
            return {"message": "Product created successfully", "productId": new_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to create product")

    @router.delete("/delete_product")
    async def delete_product(request: DeleteProductModel, user: TokenModel = Depends(get_current_user_from_token)):
        if user.KindOfUser != "receptor":
             raise HTTPException(status_code=403, detail="Unauthorized access: Only receivers can delete products")

        return ProductHelper().delete_product(request)
       
    @router.get("/get_products")
    async def get_products(user: TokenModel = Depends(get_current_user_from_token)):
        if user.KindOfUser != "receptor":
            raise HTTPException(status_code=403, detail="Unauthorized access: Only receivers can list products")

        return ProductHelper().list_products()
