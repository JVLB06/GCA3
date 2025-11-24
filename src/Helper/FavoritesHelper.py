from src.Helper.ConnectionHelper import ConnectionHelper
from src.Model.FavoriteModel import FavoriteModel
from src.Model.AddFavoriteModel import AddFavoriteModel
from datetime import datetime
from fastapi import HTTPException

class FavoriteHelper(ConnectionHelper):
    def add_favorite(self, fav_info: AddFavoriteModel):
        
        connection = self.Connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")

        try:
            cursor = connection.cursor()
            cursor.execute("SELECT id_favorito FROM favoritos WHERE id_usuario = %s AND id_causa = %s", (user_id, cause_id))
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="Cause already favorited")

            else:
                cursor.execute(
                    "INSERT INTO favoritos (id_usuario, id_causa, data_cadastro) VALUES (%s, %s, %s)",
                    (fav_info.UserId, fav_info.CauseId, datetime.now())
                )
            connection.commit()
            return {"message": f"Cause with ID {fav_info.CauseId} favorited successfully"}
        
        except HTTPException:
            raise
        except Exception as e:
            connection.rollback()
            raise HTTPException(status_code=500, detail=f"Error favoriting cause: {e}")
        finally:
            connection.close()

    def remove_favorite(self, fav_id: int):
        connection = self.Connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT id_favorito FROM favoritos WHERE id_favorito = %s", (fav_id,))
            
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Favorite not found")
            
            cursor.execute("DELETE FROM favoritos WHERE id_favorito = %s", (fav_id,))
            connection.commit()
            return {"message": f"Favorite with ID {fav_id} removed successfully"}
        except HTTPException:
            raise
        except Exception as e:
            connection.rollback()
            raise HTTPException(status_code=500, detail=f"Error removing favorite: {e}")
        finally:
            connection.close()

    def list_favorites(self, user_id: int):
        connection = self.Connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        try:
            cursor = connection.cursor()
            cursor.execute("""SELECT u.nome, u.descricao, u.cep, u.documento 
                            FROM favoritos f 
                           INNER JOIN usuarios u ON f.id_favorito = u.id_usuario
                           WHERE id_usuario = %s""", (user_id,))
            
            favorites: list[FavoriteModel] = []
            rows = cursor.fetchall()

            for row in rows:
                model = FavoriteModel()
                model.CauseName=row[0]
                model.CauseDescription=row[1]
                model.CauseAddress=row[2]
                model.CauseDocument=row[3]
                
                favorites.append(model)

            return favorites
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error listing favorites: {e}")
        finally:
            connection.close()
        