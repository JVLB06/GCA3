from src.Model.PixValidationModel import PixValidationModel
from src.Model.PixDeleteModel import PixDeleteModel
from src.Model.PixModel import PixModel
from src.Helper.ConnectionHelper import ConnectionHelper
from fastapi import HTTPException
import psycopg2 as pg

class PixHelper(ConnectionHelper):
    def validate_pix_key(self, pix: PixValidationModel) -> bool:
        conection = self.Connection()
        if not conection:
            raise HTTPException(status_code=503, detail="Connection error")
        
        cursor = conection.cursor()
        try:
            query = """SELECT COUNT(1) FROM pix_chaves WHERE 
            id_usuario = %s"""
            cursor.execute(query, (str(pix.UserId)))
            result = cursor.fetchone()
            return result[0] == 0 
        except pg.Error as e:
            raise HTTPException(status_code=403, detail=f"Error validating PIX key: {e}")
        finally:
            cursor.close()
            self.CloseConnection(conection)

    def add_pix_key(self, pix: PixModel) -> str:
        conection = self.Connection()
        if not conection:
            raise HTTPException(status_code=503, detail="Connection error")
        
        pixValidate = PixValidationModel()
        pixValidate.UserId = pix.UserId
        pixValidate.PixKey = pix.PixKey
        pixValidate.KeyType = pix.KeyType

        if self.validate_pix_key(pixValidate):

            cursor = conection.cursor()
            
            try:
                query = """INSERT INTO pix_chaves (id_usuario, chave, tipo_chave, data_cadastro)
                VALUES (%s, %s, %s, %s)"""
                cursor.execute(query, (pix.UserId, pix.PixKey, pix.KeyType, pix.CreatedAt))
                conection.commit()
                return "Pix key added successfully"
            except pg.Error as e:
                raise HTTPException(status_code=500, detail=f"Error during adding pix key: {e}")
            finally:
                cursor.close()
                self.CloseConnection(conection)
        else:
            raise HTTPException(status_code=409, detail="PIX key already exists")
        
    def delete_pix_key(self, pix: PixDeleteModel) -> str:
        conection = self.Connection()
        if not conection:
            raise HTTPException(status_code=503, detail="Connection error")
        
        pixValidate = PixValidationModel()
        pixValidate.UserId = pix.UserId

        if self.validate_pix_key(pixValidate):

            raise HTTPException(status_code=404, detail="PIX key not found")
        
        else:

            cursor = conection.cursor()

            try:
                query = """DELETE FROM pix_chaves WHERE 
                id_usuario = %s AND id_chave = %s"""
                cursor.execute(query, (pix.UserId, pix.PixId))
                conection.commit()
                return "Pix key deleted successfully"
            except pg.Error as e:
                raise HTTPException(status_code=500, detail=f"Error during deleting pix key: {e}")
            finally:
                cursor.close()
                self.CloseConnection(conection)
