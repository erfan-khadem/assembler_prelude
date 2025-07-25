from typing import Protocol

class MachineCodeListener(Protocol):
    """Protocol for listeners receiving generated machine instructions."""
    def add(self, instr: int):
        """Adds an instruction word to the machine program."""
        ...

