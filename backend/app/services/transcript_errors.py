
class TranscriptIngestionError(Exception):
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
