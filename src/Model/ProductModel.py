from pydantic import BaseModel

class ProductModel(BaseModel):
    productId: int 
    causeId: int
    name: str
    description: str
    value: float
 