from pydantic import BaseModel

class AddFavoriteModel(BaseModel):
    CauseId: int
    UserId: int