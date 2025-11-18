from fastapi import HTTPException, Request
from src.Helper.TokenHelper import TokenHelper

async def authenticate_request(request: Request, call_next):
    """
    Middleware para validar tokens em rotas protegidas.
    Rotas públicas não exigem token.
    """
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

def add_security_middleware(app):
    """
    Função auxiliar para adicionar o middleware de segurança ao app FastAPI.
    """
    app.middleware("http")(authenticate_request)