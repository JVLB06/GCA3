from pydantic import BaseModel

class DeactivateModel(BaseModel):
    id_usuario: int  # ID do usuário a ser inativado