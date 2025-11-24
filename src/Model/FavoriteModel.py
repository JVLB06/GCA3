from pydantic import BaseModel

class FavoriteModel(BaseModel):
    CauseName: str
    CauseDescription: str
    CauseAddress: str
    CauseDocument: str