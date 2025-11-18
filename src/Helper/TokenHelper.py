import jwt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

class TokenHelper:
    def __init__(self):
        # Inicializa as variáveis como atributos de instância
        self.secret_key = "my_secret_key"  # Chave secreta fixa para desenvolvimento (mudar para .env depois se possivel)
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60  # Expiração em minutos (1 hora)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """
        Gera um token JWT com os dados fornecidos.
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=self.access_token_expire_minutes))
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verifica e decodifica um token JWT. Retorna os dados se válido, None se inválido.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None  # Token expirado
        except jwt.InvalidTokenError:
            return None  # Token inválido

    def get_current_user(self, token: str) -> Optional[str]:
        """
        Extrai o username do token (útil para rotas protegidas).
        """
        payload = self.verify_token(token)
        if payload:
            return payload.get("sub")  # "sub" é o campo padrão para o usuário
        return None