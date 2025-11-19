from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.Helper.TokenHelper import TokenHelper

# esquema HTTP Bearer para Swagger (cadeado)
security_scheme = HTTPBearer()

# Rotas públicas (não exigem token)
PUBLIC_ROUTES = {
    "/",
    "/login",
    "/cadastrate",
    "/docs",
    "/redoc",
    "/openapi.json",
}

async def authenticate_request(request: Request, call_next):
    """
    Middleware para validar tokens em rotas protegidas.
    Rotas públicas não exigem token.
    """
    path = request.url.path

    # Libera docs e variantes
    if (
        path in PUBLIC_ROUTES
        or path.startswith("/docs")
        or path.startswith("/openapi")
    ):
        return await call_next(request)
    
    # Verifica token no header Authorization
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token missing or invalid")
    
    token = auth_header.split(" ", 1)[1]

    # ✅ instância do TokenHelper
    token_helper = TokenHelper()
    user = token_helper.get_current_user(token)

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


# ===== Dependency para usar nas rotas protegidas (Swagger sabe usar) =====

async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
):
    """
    Dependency usada nas rotas protegidas.
    Faz o Swagger exibir o cadeado e valida o token.
    """
    token = credentials.credentials  # só o token, sem "Bearer "

    token_helper = TokenHelper()
    user = token_helper.get_current_user(token)

    if not user:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    return user
