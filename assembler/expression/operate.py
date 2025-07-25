from enum import Enum
from typing import Optional
from .expression import Expression
from .context import Context
from .expression_exception import ExpressionException

class Operation(Enum):
    OR = "|"
    AND = "&"
    MUL = "*"
    ADD = "+"
    XOR = "^"
    DIV = "/"
    SUB = "-"

    @property
    def op_str(self) -> str:
        return self.value

class Operate(Expression):
    """Represents a binary operation between two expressions."""
    def __init__(self, a: Expression, op: Operation, b: Expression):
        self.a = a
        self.op = op
        self.b = b

    def get_value(self, context: Optional[Context]) -> int:
        av = self.a.get_value(context)
        bv = self.b.get_value(context)
        match self.op:
            case Operation.OR:  return av | bv
            case Operation.AND: return av & bv
            case Operation.XOR: return av ^ bv
            case Operation.ADD: return av + bv
            case Operation.SUB: return av - bv
            case Operation.MUL: return av * bv
            case Operation.DIV:
                if bv == 0:
                    raise ExpressionException("Division by zero")
                # Integer division
                return av // bv
        # Should not happen if enum is exhaustive
        raise ExpressionException(f"Operation {self.op.name} not supported!")

    @staticmethod
    def check_brace(expr: Expression) -> str:
        """Add parentheses if the expression is another operation for clarity."""
        if isinstance(expr, Operate):
            return f"({expr})"
        else:
            return str(expr)

    def __str__(self) -> str:
        return f"{Operate.check_brace(self.a)}{self.op.op_str}{Operate.check_brace(self.b)}"

    def __repr__(self) -> str:
        return f"Operate({repr(self.a)}, Operation.{self.op.name}, {repr(self.b)})"


