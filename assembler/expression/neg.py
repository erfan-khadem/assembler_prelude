from typing import Optional
from .expression import Expression
from .context import Context
from .expression_exception import ExpressionException
from .operate import Operate # For check_brace

class Neg(Expression):
    """Expression which negates another expression."""
    def __init__(self, value: Expression):
        self.value = value

    def get_value(self, context: Optional[Context]) -> int:
        return -self.value.get_value(context)

    def __str__(self) -> str:
        return f"-{Operate.check_brace(self.value)}"

    def __repr__(self) -> str:
        return f"Neg({repr(self.value)})"
