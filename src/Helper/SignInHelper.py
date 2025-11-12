import psycopg2 as pg
from src.Helper.ConnectionHelper import ConnectionHelper
from Model import CadastrateModel, LoginModel

class SignInHelper(ConnectionHelper):
    def __init__(self):
        pass

    def SignIn(self, params: LoginModel.LoginModel) -> bool:
        connection = self.Connection()
        if not connection:
            return False

        try:
            cursor = connection.cursor()
            query = "SELECT COUNT(1) FROM users WHERE username = %s AND password = %s"
            cursor.execute(query, (params.username, params.password))
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
                INSERT INTO users (name, email, password, is_receiver, cause, document)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                params.Name,
                params.Email,
                params.Password,
                params.IsReceiver,
                params.Cause,
                params.Document
            ))
            connection.commit()
            cursor.close()
            return True
        except pg.Error as e:
            print(f"Error during cadastrate: {e}")
            return False
        finally:
            self.CloseConnection(connection)