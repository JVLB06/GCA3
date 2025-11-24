from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from src.Model.PixModel import PixModel
from src.Model.PixDeleteModel import PixDeleteModel
from src.Model.DeactivateModel import DeactivateModel  
from src.Helper.PixHelper import PixHelper as ph
from src.Helper.SecurityHelper import get_current_user_from_token
from src.Helper.ConnectionHelper import ConnectionHelper  
from src.Helper.SignInHelper import SignInHelper  

class ReceiverController:
    
    router = APIRouter(prefix="/receiver", tags=["Receiver"])

    @router.get("/")
    async def get_receiver():
        return {"message": "Receiver endpoint is working!"}
    
    @router.post("/add_pix_key")
    async def add_pix_key(request: PixModel,
        user: str = Depends(get_current_user_from_token)):
        
        if user != "recebedor":
            raise HTTPException(status_code=403, detail="Unauthorized access: Only receivers can access this endpoint")
        
        if not request.CreatedAt:
            request.CreatedAt = datetime.now().isoformat()

        return {"message": ph().add_pix_key(request)}
    
    @router.delete("/delete_pix_key")
    async def delete_pix_key(request: PixDeleteModel,
        user: str = Depends(get_current_user_from_token)):

        if user != "recebedor":
            raise HTTPException(status_code=403, detail="Unauthorized access: Only receivers can access this endpoint")
        
        return {"message": ph().delete_pix_key(request)}

    # Novo endpoint para inativação de receptor
    @router.post("/deactivate")
    async def deactivate_receiver(request: DeactivateModel, user_email: str = Depends(get_current_user_from_token)):
        # Buscar dados do usuário logado via email (do token)
        signin_helper = SignInHelper()
        user_data = signin_helper.GetKindOfUser(user_email)
        user_id = user_data.UserId
        user_type = user_data.KindOfUser

        # Verificar se é receptor ou admin
        if user_type not in ['receptor', 'admin']:  # Nota: assumindo 'recebedor' como 'receptor' no enum
            raise HTTPException(status_code=403, detail="Unauthorized: Only receivers or admins can deactivate receivers")

        # Se não for admin, só pode inativar si mesmo
        if user_type != 'admin' and request.id_usuario != user_id:
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