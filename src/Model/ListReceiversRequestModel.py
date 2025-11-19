from pydantic import BaseModel
from typing import Optional

class ListReceiversRequestModel(BaseModel):
    TypeOfOrder: Optional[str] | None = None