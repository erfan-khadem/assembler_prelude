from abc import ABC, abstractmethod
from .context import Context
from .expression_exception import ExpressionException


from typing import Optional

class Expression(ABC):
    """Base class for all expressions."""
    @abstractmethod
    def get_value(self, context: Optional[Context]) -> int:
        """
        Returns the integer value of this expression.
        Context can be None for simple constants if needed.
        """
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass

