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

