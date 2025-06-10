class SubscriptionError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message
        self.code = "x000000a"
    
    def __str__(self):
        return f"{self.code}: {self.message}"

class ClientNotExistsError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message
        self.code = "x000000b"
    
    def __str__(self):
        return f"{self.code}: {self.message}"