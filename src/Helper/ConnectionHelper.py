import psycopg2 as pg

class ConnectionHelper:
    def __init__(self, database, user, password, host, port):
        self.Database = database
        self.User = user
        self.Password = password
        self.Host = host
        self.Port = port

    def Connection(self):
        try:
            connection = pg.connect(
                database=self.Database,
                user=self.User,
                password=self.Password,
                host=self.Port,
                port=self.Host
            )
            return connection
        except pg.Error as e:
            print(f"Error connecting to database: {e}")
            return None
        
    def CloseConnection(self, connection: pg.extensions.connection):
        if connection:
            connection.close()