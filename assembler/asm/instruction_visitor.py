from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from assembler.expression import Context, ExpressionException

if TYPE_CHECKING:
    from .instruction_interface import InstructionInterface

class InstructionVisitor(ABC):
    """Abstract base class for visiting instructions in a program."""
    @abstractmethod
    def visit(self, instruction: 'InstructionInterface', context: Context) -> bool:
        """
        Visits an instruction.
        Return False to stop iteration.
        """
        pass
