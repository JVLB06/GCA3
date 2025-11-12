class CadastrateModel:
    def __init__(self, email: str, password: str, 
                 isReceiver: bool, document: str, name: str, cause: str):
        self.Email = email
        self.Name =  name
        self.Password = password
        self.IsReceiver = isReceiver
        self.Document = document
        self.Cause = cause