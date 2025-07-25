from typing import Optional
from assembler.expression import Context, ExpressionException
from .instruction_interface import InstructionInterface
from .machine_code_listener import MachineCodeListener

class DataInstruction(InstructionInterface):
    """Used to store a data word in program memory (Von Neumann style)."""

    def __init__(self, value: int, line_num: int, label: Optional[str]):
        self._value = value
        self._line_num = line_num
        self._label = label
        self._abs_addr = -1 # Can be set by Program/Directives if needed

    @property
    def abs_addr(self) -> int:
        return self._abs_addr

    @abs_addr.setter
    def abs_addr(self, value: int):
         self._abs_addr = value

    @property
    def line_number(self) -> int:
        return self._line_num

    @property
    def size(self) -> int:
        return 1 # Data words are always 1 word

    @property
    def label(self) -> Optional[str]:
        return self._label

    def create_machine_code(self, context: Context, machine_code_listener: MachineCodeListener):
        # Data instructions just emit their value directly
        # Mask to 16 bits if the architecture requires it
        machine_code_listener.add(self._value & 0xFFFF)

    @property
    def macro_description(self) -> Optional[str]:
        return None # Data is not from a macro in this sense

    @property
    def comment(self) -> Optional[str]:
         return None # Comments handled separately by Program if needed

    def _get_char_repr(self) -> str:
        """Helper for __str__ to represent the value as a character if possible."""
        val = self._value & 0xFFFF
        if 32 <= val <= 126:
            return chr(val)
        else:
            escape_map = {
                ord('\n'): '\\n', ord('\r'): '\\r', ord('\t'): '\\t', ord('\0'): '\\0'
            }
            return escape_map.get(val, f"#{val}")

    def __str__(self) -> str:
        char_repr = self._get_char_repr()
        return f".data '{char_repr}', {self._value}" # Approximate representation

    def __repr__(self) -> str:
        return f"DataInstruction(value={self._value}, line={self._line_num}, label={self._label})"

