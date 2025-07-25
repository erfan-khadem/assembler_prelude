from typing import Optional
from assembler.expression import Expression, Constant, Neg
from .register import Register
from .opcode import Opcode
from .instruction import Instruction
from .instruction_exception import InstructionException

class InstructionBuilder:
    """A builder to create an Instruction with validation."""

    def __init__(self, opcode: Opcode):
        self._opcode = opcode
        self._source: Optional[Register] = None
        self._dest: Optional[Register] = None
        self._constant: Optional[Expression] = None

    def set_source(self, source: Register) -> 'InstructionBuilder':
        if not self._opcode.arguments.has_source:
            raise InstructionException(f"{self._opcode.name} needs no source register!")
        if self._source is not None:
            raise InstructionException(f"{self._opcode.name} source set twice!")
        self._source = source
        return self

    def set_dest(self, dest: Register) -> 'InstructionBuilder':
        if not self._opcode.arguments.has_dest:
            raise InstructionException(f"{self._opcode.name} needs no destination register!")
        if self._dest is not None:
            raise InstructionException(f"{self._opcode.name} destination set twice!")
        self._dest = dest
        return self

    def set_constant_int(self, value: int) -> 'InstructionBuilder':
        return self.set_constant(Constant(value))

    def set_constant(self, constant: Expression) -> 'InstructionBuilder':
        if not self._opcode.arguments.has_const:
            raise InstructionException(f"{self._opcode.name} needs no constant!")
        if self._constant is not None:
            raise InstructionException(f"{self._opcode.name} constant set twice!")
        self._constant = constant
        return self

    def neg_constant(self) -> 'InstructionBuilder':
        if self._constant is None:
             raise InstructionException(f"Cannot negate non-existent constant for {self._opcode.name}")
        self._constant = Neg(self._constant)
        return self

    def build(self) -> Instruction:
        args = self._opcode.arguments
        if args.has_source and self._source is None:
            raise InstructionException(f"{self._opcode.name} needs a source register!")
        if args.has_dest and self._dest is None:
            raise InstructionException(f"{self._opcode.name} needs a destination register!")
        if args.has_const and self._constant is None:
            raise InstructionException(f"{self._opcode.name} needs a constant!")

        # Default to R0 if registers are not required but builder slots exist
        dest = self._dest if self._dest is not None else Register.R0
        source = self._source if self._source is not None else Register.R0

        return Instruction(self._opcode, dest, source, self._constant)

