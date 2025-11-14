import psycopg2 as pg
from src.Helper.ConnectionHelper import ConnectionHelper
from src.Model import CadastrateModel, LoginModel

class SignInHelper(ConnectionHelper):
    def SignIn(self, params: LoginModel.LoginModel) -> bool:
        connection = self.Connection()
        if not connection:
            return False

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
            return False

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