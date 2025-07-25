from .expression_exception import ExpressionException

from typing import Dict, Optional

class Context:
    """The context needed to evaluate an expression, holding identifiers and the current address."""
    # Static identifiers (class variables)
    SKIP_ADDR = "_SKIP_ADDR_"
    NEXT_ADDR = "_NEXT_ADDR_"
    SKIP2_ADDR = "_SKIP2_ADDR_"
    ADDR = "_ADDR_"

    def __init__(self):
        self._identifier: Dict[str, int] = {}
        self._instr_addr: int = 0
        self._identifier[Context.ADDR.lower()] = 0 # Initialize ADDR

    def get(self, name: str) -> int:
        """Returns the named value."""
        key = name.lower() # Convert to lower case for lookup
        value = self._identifier.get(key)
        if value is None:
            # Keep original case in error message
            raise ExpressionException(f"'{name}' not found")
        return value


    def add_identifier(self, name: str, value: int) -> 'Context':
        """Adds an identifier (case-insensitive). Raises error if exists with a different value."""
        key = name.lower() # Convert to lower case
        existing_value = self._identifier.get(key)
        if existing_value is not None and existing_value != value:
            # Show original case in error message
            raise ExpressionException(f"Label '{name}' defined twice (case-insensitive) with different values: {existing_value} and {value}")
        return self.set_identifier(name, value) # Use set_identifier

    def set_identifier(self, name: str, value: int) -> 'Context':
        """Sets a named value (case-insensitive), overwriting if it exists."""
        key = name.lower() # Convert to lower case
        self._identifier[key] = value
        # Update special identifiers case-insensitively too
        if name == Context.ADDR: self._instr_addr = value
        return self

    def set_instr_addr(self, instr_addr: int) -> 'Context':
        """Sets the address of the actual instruction."""
        self._instr_addr = instr_addr
        # Use set_identifier to handle case correctly
        return self.set_identifier(Context.ADDR, instr_addr)

    @property
    def instr_addr(self) -> int:
        """Returns the address of the actual instruction."""
        return self._instr_addr

    def __str__(self) -> str:
        return f"Context(addr={self._instr_addr}, identifiers={self._identifier})"
