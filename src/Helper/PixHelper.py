from src.Model.PixValidationModel import PixValidationModel
from src.Model.PixModel import PixModel
from src.Helper.ConnectionHelper import ConnectionHelper
from fastapi import HTTPException
import psycopg2 as pg

class PixHelper (ConnectionHelper):
    def __init__(self):
        pass
    
    def validate_pix_key(self, pix: PixValidationModel) -> bool:
        conection = self.Connection()
        if not conection:
            raise HTTPException(status_code=503, detail="Connection error")
        
        cursor = conection.cursor()
        try:
            query = """SELECT COUNT(1) FROM pix_chaves WHERE chave = %s
            AND tipo_chave = %s AND id_usuario = %s"""
            cursor.execute(query, (pix.PixKey, pix.KeyType, pix.UserId))
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
        
        if not self.validate_pix_key(PixValidationModel(
            UserId=pix.UserId,
            PixKey=pix.PixKey,
            KeyType=pix.KeyType)):

            cursor = conection.cursor()
            
            try:
                query = """INSERT INTO pix_chaves (id_usuario, chave, tipo_chave, criado_em)
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
        
    def delete_pix_key(self, pix: PixModel) -> str:
        conection = self.Connection()
        if not conection:
            raise HTTPException(status_code=503, detail="Connection error")
        
        if self.validate_pix_key(PixValidationModel(
            UserId=pix.UserId,
            PixKey=pix.PixKey,
            KeyType=pix.KeyType)):

            raise HTTPException(status_code=404, detail="PIX key not found")
        
        else:

            cursor = conection.cursor()

            try:
                query = """DELETE FROM pix_chaves WHERE chave = %s
                AND tipo_chave = %s AND id_usuario = %s"""
                cursor.execute(query, (pix.PixKey, pix.KeyType, pix.UserId))
                conection.commit()
                return "Pix key deleted successfully"
            except pg.Error as e:
                raise HTTPException(status_code=500, detail=f"Error during deleting pix key: {e}")
            finally:
                cursor.close()
                self.CloseConnection(conection)
