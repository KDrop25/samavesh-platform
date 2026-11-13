class AppError(Exception):
    """Business-rule failure. `code` is a stable key the UI translates (en/hi)."""

    def __init__(self, status: int, code: str, message: str = ""):
        self.status, self.code, self.message = status, code, message or code
