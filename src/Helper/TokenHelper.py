import jwt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

class TokenHelper:
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")  # Carrega do .env;
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Expiração em minutos (1 hora)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """
        Gera um token JWT com os dados fornecidos.
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=TokenHelper.ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, TokenHelper.SECRET_KEY, algorithm=TokenHelper.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """
        Verifica e decodifica um token JWT. Retorna os dados se válido, None se inválido.
        """
        try:
            payload = jwt.decode(token, TokenHelper.SECRET_KEY, algorithms=[TokenHelper.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None  # Token expirado
        except jwt.InvalidTokenError:
            return None  # Token inválido

    @staticmethod
    def get_current_user(token: str) -> Optional[str]:
        """
        Extrai o username do token (útil para rotas protegidas).
        """
        payload = TokenHelper.verify_token(token)
        if payload:
            return payload.get("sub")  # "sub" é o campo padrão para o usuário

        return None
