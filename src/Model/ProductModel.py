from pydantic import BaseModel

class ProductModel(BaseModel):
    CauseId: int
    Name: str
    Description: str
    Value: float
 