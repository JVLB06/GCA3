from fastapi import FastAPI
import uvicorn
from src.Controller.LoginController import LoginController

app = FastAPI()

# Rotas principais
@app.get("/")
async def root():
    return {"message": "Welcome to the GQSA3 API"}

# Incluindo routers
app.include_router(LoginController.router)

# Iniciar o servidor
if __name__ == "__main__":
    uvicorn.run(
        "MainController:app",   # nome_do_arquivo:variavel_app
        host="0.0.0.0",
        port=8000,
        reload=True   # remove em produção
    )
