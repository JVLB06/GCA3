import psycopg2 as pg

class ConnectionHelper:
    def __init__(self):
        self.Database = "helper"
        self.User = "postgres"
        self.Password = "2006"
        self.Host = "localhost"
        self.Port = 5432

    def Connection(self):
        try:
            connection = pg.connect(
                database=self.Database,
                user=self.User,
                password=self.Password,
                host=self.Host,
                port=self.Port
            )
            return connection
        except pg.Error as e:
            print(f"Error connecting to database: {e}")
            return None
        
    def CloseConnection(self, connection: pg.extensions.connection):
        if connection:
            connection.close()