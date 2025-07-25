import math
from typing import Optional
from .expression import Expression
from .context import Context

class Constant(Expression):
    """Represents a constant integer or character value."""
    def __init__(self, value: int | str):
        if isinstance(value, str):
            if len(value) != 1:
                raise ValueError(f"String constant must be a single character. Got '{value}'")
            self._value = ord(value)
            self._is_char = True
        elif isinstance(value, int):
            # Ensure value fits within reasonable bounds if necessary,
            # Python ints have arbitrary precision, but hardware might not.
            # For now, accept any int.
             self._value = value
             self._is_char = False
        else:
            raise TypeError("Constant value must be int or single char string")

    def get_value(self, context: Optional[Context]) -> int:
        return self._value

    def __str__(self) -> str:
        if self._is_char:
            char = chr(self._value)
            # Escape special characters for string representation
            escape_map = {
                    '\n': '\\n', '\r': '\\r', '\t': '\\t', '\b': '\\b',
                    '\'': '\\\'', '\"': '\\"', '\\': '\\\\', '\0': '\\0' # Add explicit handling for \0
                    }
            if char in escape_map:
                return f"'{escape_map[char]}'"
            elif 32 <= self._value < 127: # Printable ASCII
                return f"'{char}'"
            else: # Other non-printable or non-ASCII
                return f"'\\x{self._value:02x}'" # Represent as hex escape
        else:
            return str(self._value)

    def __repr__(self) -> str:
        return f"Constant({self.__str__()})"

