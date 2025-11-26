from pydantic import BaseModel

class DeleteProductModel(BaseModel):
    ProductId: int