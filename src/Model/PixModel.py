from pydantic import BaseModel

class PixModel(BaseModel):
    UserId: int
    PixKey: str
    KeyType: str
    CreatedAt: str