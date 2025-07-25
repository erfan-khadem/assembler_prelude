class InstructionException(Exception):
    """Custom exception for instruction format or building errors."""
    def __init__(self, message: str):
        super().__init__(message)

