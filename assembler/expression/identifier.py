from typing import Optional
from .expression import Expression
from .context import Context
from .expression_exception import ExpressionException

class Identifier(Expression):
    """Represents an identifier (label or variable name) in an expression."""
    def __init__(self, name: str):
        if not name:
            raise ValueError("Identifier name cannot be empty")
        self.name = name

    def get_value(self, context: Optional[Context]) -> int:
        if context is None:
            raise ExpressionException(f"Context required to evaluate identifier '{self.name}'")
        return context.get(self.name)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Identifier({self.name})"

