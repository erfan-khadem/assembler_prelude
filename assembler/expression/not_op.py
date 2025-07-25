from typing import Optional
from .expression import Expression
from .context import Context
from .expression_exception import ExpressionException
from .operate import Operate # For check_brace

class NotOp(Expression): # Renamed from Not to avoid conflict
    """Performs a bitwise not on an expression."""
    def __init__(self, value: Expression):
        self.value = value

    def get_value(self, context: Optional[Context]) -> int:
        # Python's ~ operator works correctly for two's complement bitwise NOT
        return ~self.value.get_value(context)

    def __str__(self) -> str:
        return f"~{Operate.check_brace(self.value)}"

    def __repr__(self) -> str:
        return f"NotOp({repr(self.value)})"
