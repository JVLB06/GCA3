from fastapi import FastAPI, HTTPException, Request
import uvicorn
from src.Controller.LoginController import LoginController
from src.Helper.TokenHelper import TokenHelper  # Novo import

app = FastAPI()

# Middleware para validar tokens em rotas protegidas
@app.middleware("http")
async def authenticate_request(request: Request, call_next):
    # Rotas públicas (não exigem token)
    public_routes = ["/", "/login", "/cadastrate"]
    if request.url.path in public_routes:
        return await call_next(request)
    
    # Verifica token no header Authorization
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token missing or invalid")
    
    token = auth_header.split(" ")[1]
    user = TokenHelper.get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    
    # Adiciona o usuário ao request para uso em rotas (opcional)
    request.state.user = user
    return await call_next(request)

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