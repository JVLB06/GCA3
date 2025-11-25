from src.Helper.ConnectionHelper import ConnectionHelper
from fastapi import HTTPException
from src.Model.DonationModel import DonationModel
from src.Model.ListDonationModel import ListDonationModel

class DonationsHelper(ConnectionHelper):
    def list_donations_by_user(self, user_id):
        connection = self.Connection()
        try:
            cursor = connection.cursor()

            query = """SELECT d.id_doacao AS id,
                    u.nome AS Doador,
                    ub.nome AS Receptor,
                    d.valor_doacao AS valor,
                    d.mensagem,
                    d.data_doacao
                FROM doacoes d
                    INNER JOIN usuarios u ON u.id_usuario = d.id_doador
                    INNER JOIN usuarios ub ON ub.id_usuario = d.id_causa 
                WHERE u.user_id = %s"""
            
            params = (user_id,)
            
            cursor.execute(query, params)
            results: list[ListDonationModel] = []

            for row in cursor.fetchall():
                donation = ListDonationModel(
                    DonationId=row[0],
                    DonorName=row[1],
                    ReceiverName=row[2],
                    Amount=row[3],
                    Message=row[4],
                    Date=row[5]
                )
                results.append(donation)
            return results

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()
            self.CloseConnection(connection)

    
    def list_donations_received(self, receiver_id):
        connection = self.Connection()
        try:
            cursor = connection.cursor()

            query = """SELECT d.id_doacao AS id,
                    u.nome AS Doador,
                    ub.nome AS Receptor,
                    d.valor_doacao AS valor,
                    d.mensagem,
                    d.data_doacao
                FROM doacoes d
                    INNER JOIN usuarios u ON u.id_usuario = d.id_doador
                    INNER JOIN usuarios ub ON ub.id_usuario = d.id_causa 
                WHERE ub.user_id = %s"""
            params = (receiver_id,)
            
            cursor.execute(query, params)
            results: list[ListDonationModel] = []

            for row in cursor.fetchall():
                donation = ListDonationModel(
                    DonationId=row[0],
                    DonorName=row[1],
                    ReceiverName=row[2],
                    Amount=row[3],
                    Message=row[4],
                    Date=row[5]
                )
                results.append(donation)
            return results
        
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()
            self.CloseConnection(connection)
    
    def add_donations(self, donation_info: DonationModel):
        connection = self.Connection()

        try:
            query = "INSERT INTO doacoes (id_doador, id_causa, valor_doacao, mensagem, data_doacao) VALUES (%s, %s, %s, %s, %s)"
            params = (donation_info.DonorId, donation_info.ReceiverId, donation_info.Amount, donation_info.Message, donation_info.Date)

            cursor = connection.cursor()
            cursor.execute(query, params)

            connection.commit()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()
            self.CloseConnection(connection)