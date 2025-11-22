from src.Helper.ConnectionHelper import ConnectionHelper
from src.Model.ListReceiversModel import ListReceiversModel
from src.Model.ListReceiversRequestModel import ListReceiversRequestModel
import psycopg2 as pg

class ReceiversHelper(ConnectionHelper):
    def get_receivers(self, param: str) -> list[ListReceiversModel]:
        
        connection = self.Connection()

        cursor = connection.cursor()

        baseQuery = """SELECT id_usuario, nome, email, documento, cep, descricao
        FROM usuarios
        WHERE ativo = true AND tipo_usuario = 'receptor'"""

        match param:
            case "name_desc":
                query = baseQuery + " ORDER BY nome DESC"
            case "created_at_desc":
                query = baseQuery + " ORDER BY data_cadastro DESC"
            case "name_asc":
                query = baseQuery + " ORDER BY nome ASC"
            case "created_at_asc":
                query = baseQuery + " ORDER BY data_cadastro ASC"
            case "":
                query = baseQuery
            case None:
                query = baseQuery

        cursor.execute(query)
        receivers: list[ListReceiversModel] = []
        rows = cursor.fetchall()

        for row in rows:
            model = ListReceiversModel()
            model.UserId=row[0]
            model.Name=row[1]
            model.Email=row[2]
            model.Document=row[3]
            model.Address=row[4]
            model.Description=row[5]
            
            receivers.append(model)
        
        cursor.close()
        connection.close()

        return receivers

    # Novo método auxiliar para validar se um cause_id é um receptor válido e ativo
    def validate_cause_id(self, cause_id: int) -> bool:
        connection = self.Connection()
        if not connection:
            return False
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id_usuario FROM usuarios WHERE id_usuario = %s AND tipo_usuario = 'receptor' AND ativo = true",
                (cause_id,)
            )
            return cursor.fetchone() is not None
        except Exception:
            return False
        finally:
            cursor.close()
            connection.close()