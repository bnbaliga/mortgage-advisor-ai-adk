"""Domain errors shared across the backend."""


class MortgageError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message
