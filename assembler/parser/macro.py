from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import io

from assembler.asm import Program, InstructionException, MnemonicArguments
from assembler.expression import ExpressionException

if TYPE_CHECKING:
    from .parser import Parser

class Macro(ABC):
    """Abstract base class for assembler macros (pseudo-instructions)."""
    def __init__(self, name: str, args: MnemonicArguments, description: str):
        self._name = name
        self._args = args
        self._description = description

    @property
    def name(self) -> str: return self._name
    @property
    def arguments(self) -> MnemonicArguments: return self._args
    @property
    def description(self) -> str: return self._description

    @abstractmethod
    def parse_macro(self, p: Program, name: str, parser: 'Parser'):
        """Parses the macro arguments and adds generated instructions to the program."""
        pass

    def __str__(self) -> str:
        return f"{self.name} {self.arguments}\n\t{self.description}"

