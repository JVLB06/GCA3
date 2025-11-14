from pydantic import BaseModel
from typing import Optional

class CadastrateModel(BaseModel):
    Email: str
    Password: str
    IsReceiver: str
    Document: Optional[str] = None
    Name: str
    Cause: Optional[str] = None
    Address: Optional[str] = None
