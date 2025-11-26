from src.Helper.ConnectionHelper import ConnectionHelper
from src.Model.ProductModel import ProductModel
from src.Model.DeleteProductModel import DeleteProductModel
from src.Model.ListProductModel import ListProductModel
from fastapi import HTTPException
from datetime import datetime

class ProductHelper(ConnectionHelper):
    def create_product(self, product: ProductModel):
        
        connection = self.Connection()
        try:      
            query = """
                INSERT INTO produtos (id_causa, nome, descricao, valor, data_cadastro)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id_produto;
            """
            
            createdAt = datetime.now()
            cursor = connection.cursor()
            
            cursor.execute(query, (
                product.CauseId,      
                product.Name,         
                product.Description,  
                product.Value,        
                createdAt             
            ))
            
            new_id = cursor.fetchone()[0]
            connection.commit()
            return {"message" : "Created new product", "ProductId" : new_id}

        except HTTPException:
            raise
        except Exception as e:
            connection.rollback()
            raise HTTPException(status_code=500, detail=f"Error creating product: {e}")
        finally:
            cursor.close()
            self.CloseConnection(connection)

    def delete_product(self, productId: DeleteProductModel):
        
        connection = self.Connection()
        cursor = connection.cursor()
        try:    
            query = """
                DELETE FROM produtos 
                WHERE id_produto = %s;
            """
            
            cursor.execute(query, (productId.ProductId,))
            
            connection.commit()
            
            return cursor.rowcount > 0

        except HTTPException:
            raise
        except Exception as e:
            connection.rollback()
            raise HTTPException(status_code=500, detail=f"Error deleting product: {e}")
        finally:
            cursor.close()
            self.CloseConnection(connection)
    
    def list_products(self, UserId: int = None):
        
        connection = self.Connection()
        cursor = connection.cursor()

        query = """SELECT id_produto, id_causa, nome, descricao, valor
        FROM produtos"""

        try:
            if UserId:
                query += " WHERE id_causa = %s"
                cursor.execute(query, (UserId,))
            else:
                cursor.execute(query)

            products: list[ListProductModel] = []
            rows = cursor.fetchall()

            for row in rows:
                model = ListProductModel()
                model.ProductId=row[0]
                model.CauseId=row[1]
                model.ProductName=row[2]
                model.Description=row[3]
                model.Value=row[4]
                
                products.append(model)
            
            return products
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error listing produtct: {e}")
        finally:
            cursor.close()
            self.CloseConnection(connection)
