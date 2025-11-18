from fastapi import FastAPI, HTTPException, Request
import uvicorn
from src.Controller.LoginController import LoginController
from src.Controller.DonatorController import DonatorController
from src.Controller.ReceiverController import ReceiverController
from src.Helper.SecurityHelper import add_security_middleware

app = FastAPI()

# Adiciona o middleware de segurança
add_security_middleware(app)

# Rotas principais
@app.get("/")
async def root():
    return {"message": "Welcome to the GQSA3 API"}

# Incluindo routers
app.include_router(LoginController.router)
app.include_router(DonatorController.router)
app.include_router(ReceiverController.router)

# Iniciar o servidor
if __name__ == "__main__":
    uvicorn.run(
        "MainController:app",   # nome_do_arquivo:variavel_app
        host="0.0.0.0",
        port=8000,
        reload=True   # remove em produção
    )