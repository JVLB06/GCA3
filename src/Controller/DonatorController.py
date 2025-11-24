from fastapi import APIRouter, HTTPException, Request, Depends
from src.Model.ListReceiversRequestModel import ListReceiversRequestModel
from src.Model.DeactivateModel import DeactivateModel  
from src.Helper.ReceiversHelper import ReceiversHelper
from src.Helper.SecurityHelper import get_current_user_from_token
from src.Helper.ConnectionHelper import ConnectionHelper 
from src.Helper.SignInHelper import SignInHelper  
from datetime import datetime 

class DonatorController:
    
    router = APIRouter(prefix="/donator", tags=["Donator"])

    @router.get("/")
    async def get_donator():
        return {"message": "Donator endpoint is working!"}
    
    @router.get("/list_receivers/{TypeOfOrder}")
    async def list_receivers(TypeOfOrder: str, user: str = Depends(get_current_user_from_token)):
        print(user)
        if user != "doador":
            raise HTTPException(status_code=403, detail="Unauthorized access: Only donators can access this endpoint")
        try:
            helper = ReceiversHelper()
            receivers = helper.get_receivers(TypeOfOrder)
            return {"receivers": receivers}
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Error fetching receivers: {e}")

    @router.post("/deactivate")
    async def deactivate_donator(request: DeactivateModel, user_email: str = Depends(get_current_user_from_token)):
        # Buscar dados do usuário logado via email (do token)
        signin_helper = SignInHelper()
        user_data = signin_helper.GetKindOfUser(user_email)
        user_id = user_data.UserId
        user_type = user_data.KindOfUser

        # Verificar se é doador ou admin
        if user_type not in ['doador', 'admin']:
            raise HTTPException(status_code=403, detail="Unauthorized: Only donators or admins can deactivate donators")

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
    async def favorite_cause(cause_id: int, user_email: str = Depends(get_current_user_from_token)):
        # Buscar dados do usuário logado via email (do token)
        signin_helper = SignInHelper()
        user_data = signin_helper.GetKindOfUser(user_email)
        user_id = user_data.UserId
        user_type = user_data.KindOfUser

        # Verificar se é doador
        if user_type != 'doador':
            raise HTTPException(status_code=403, detail="Unauthorized: Only donators can favorite causes")

        # Validar se o cause_id é um receptor válido e ativo
        receivers_helper = ReceiversHelper()
        if not receivers_helper.validate_cause_id(cause_id):
            raise HTTPException(status_code=404, detail="Cause not found or not active")

        # Conectar ao banco
        conn_helper = ConnectionHelper()
        connection = conn_helper.Connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")

        try:
            cursor = connection.cursor()
            # Verificar se já está favoritado (evitar duplicatas)
            cursor.execute("SELECT id_favorito FROM favoritos WHERE id_usuario = %s AND id_causa = %s", (user_id, cause_id))
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="Cause already favorited")

            # Inserir favorito
            cursor.execute(
                "INSERT INTO favoritos (id_usuario, id_causa, data_cadastro) VALUES (%s, %s, %s)",
                (user_id, cause_id, datetime.now())
            )
            connection.commit()
            return {"message": f"Cause with ID {cause_id} favorited successfully"}
        except HTTPException:
            raise
        except Exception as e:
            connection.rollback()
            raise HTTPException(status_code=500, detail=f"Error favoriting cause: {e}")
        finally:
            conn_helper.CloseConnection(connection)