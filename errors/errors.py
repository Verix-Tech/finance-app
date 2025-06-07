class SubscriptionError(Exception):
    def __init__(self):
        super().__init__("Erro: cliente sem assinatura.")
        self.message = "Erro: cliente sem assinatura."
        self.code = "x000000a"
    
    def __str__(self):
        return f"{self.code}: {self.message}"

class ClientNotExistsError(Exception):
    def __init__(self):
        super().__init__("Erro: cliente não existe no banco de dados.")
        self.message = "Erro: cliente não existe no banco de dados."
        self.code = "x000000b"
    
    def __str__(self):
        return f"{self.code}: {self.message}"