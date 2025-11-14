from pydantic import BaseModel

class LoginModel(BaseModel):
    Username: str
    Password: str