import psycopg2 as pg
import re
import requests
from fastapi import HTTPException
from src.Helper.ConnectionHelper import ConnectionHelper
from src.Model import CadastrateModel, LoginModel, TokenModel

class SignInHelper(ConnectionHelper):
    def SignIn(self, params: LoginModel.LoginModel) -> bool:
        connection = self.Connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")

        try:
            cursor = connection.cursor()
            query = "SELECT COUNT(1) FROM usuarios WHERE email = %s AND senha = %s"
            cursor.execute(query, (params.Username, params.Password))
            result = cursor.fetchone()
            cursor.close()
            return result[0] == 1
        except pg.Error as e:
            print(f"Error during sign-in: {e}")
            return False
        finally:
            self.CloseConnection(connection)

    def Cadastrate(self, params: CadastrateModel.CadastrateModel) -> bool:
        connection = self.Connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")

        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO usuarios (nome, email, senha, tipo_usuario, descricao, documento, cep, ativo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, true)
            """
            cursor.execute(query, (
                params.Name,
                params.Email,
                params.Password,
                params.IsReceiver,
                params.Cause,
                params.Document,
                params.Address
            ))
            connection.commit()
            cursor.close()
            return True
        except pg.Error as e:
            print(f"Error during cadastrate: {e}")
            return False
        finally:
            self.CloseConnection(connection)

    def GetKindOfUser(self, email: str) -> TokenModel.TokenModel:
        connection = self.Connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = connection.cursor()
        query = "SELECT id_usuario, tipo_usuario FROM usuarios WHERE email = %s"
        cursor.execute(query, (email,))
        result = cursor.fetchone()
        cursor.close()
        res = TokenModel.TokenModel()
        res.UserId = result[0]
        res.KindOfUser = result[1]
        return res
    
    def ValidateAddress(self, address: str) -> bool:
        # mantém só dígitos
        cep_digits = re.sub(r"\D", "", address)

        # CEP precisa ter 8 dígitos
        if len(cep_digits) != 8:
            return False

        session = requests.Session()
        url = f"https://viacep.com.br/ws/{cep_digits}/json/"

        try:
            resp = session.get(url, timeout=5)
        except requests.RequestException:
            # erro de rede -> você pode decidir se isso deve ser True/False
            return False

        if resp.status_code != 200:
            return False

        data = resp.json()

        # ViaCEP retorna {"erro": true} quando o CEP não existe
        if data.get("erro") is True:
            return False

        return True
