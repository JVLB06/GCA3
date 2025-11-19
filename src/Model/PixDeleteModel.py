from pydantic import BaseModel

class PixDeleteModel(BaseModel):
    UserId: int
    PixId: int