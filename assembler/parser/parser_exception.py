class ParserException(Exception):
    """Custom exception for parsing errors."""
    def __init__(self, message: str, line_number: int = 0):
        super().__init__(message)
        self.line_number = line_number

    def set_line_number(self, line_number: int):
        if self.line_number <= 0:
            self.line_number = line_number

    def __str__(self) -> str:
        if self.line_number > 0:
            return f"line {self.line_number}: {super().__str__()}"
        else:
            return super().__str__()

