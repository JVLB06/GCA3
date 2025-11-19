from pydantic import BaseModel
from typing import Optional

class ListReceiversRequestModel(BaseModel):
    UserId: int
    TypeOfOrder: Optional[str]