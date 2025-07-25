# This requires the Parser class later for the parse method implementation
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict
from .instruction import Instruction
from .instruction_exception import InstructionException
from assembler.expression import Expression, Constant, Operate, Operation, ExpressionException, Neg


# Avoid circular import at runtime, only use for type hints
if TYPE_CHECKING:
    from ..parser.parser import Parser # Use string literal if still problematic
    from .instruction_builder import InstructionBuilder


class MnemonicArguments(ABC):
    """Describes the arguments an opcode expects."""
    def __init__(self, has_source: bool, has_dest: bool, has_const: bool):
        self._has_source = has_source
        self._has_dest = has_dest
        self._has_const = has_const

    @property
    def has_source(self) -> bool: return self._has_source
    @property
    def has_dest(self) -> bool: return self._has_dest
    @property
    def has_const(self) -> bool: return self._has_const

    @abstractmethod
    def format(self, i: Instruction) -> str:
        """Formats the arguments of an instruction."""
        pass

    @abstractmethod
    def parse(self, ib: 'InstructionBuilder', p: 'Parser'):
        """Parses the arguments using the parser and updates the instruction builder."""
        pass

    @abstractmethod
    def __str__(self) -> str:
        """String representation for documentation."""
        pass

# --- Concrete Implementations ---

class Nothing(MnemonicArguments):
    def __init__(self): super().__init__(False, False, False)
    def format(self, i: Instruction) -> str: return ""
    def parse(self, ib: 'InstructionBuilder', p: 'Parser'): return # No args
    def __str__(self) -> str: return ""

class Source(MnemonicArguments):
    def __init__(self): super().__init__(True, False, False)
    def format(self, i: Instruction) -> str: return i.source_reg.name
    def parse(self, ib: 'InstructionBuilder', p: 'Parser'): ib.set_source(p.parse_reg())
    def __str__(self) -> str: return "Rs"

class Dest(MnemonicArguments):
    def __init__(self): super().__init__(False, True, False)
    def format(self, i: Instruction) -> str: return i.dest_reg.name
    def parse(self, ib: 'InstructionBuilder', p: 'Parser'): ib.set_dest(p.parse_reg())
    def __str__(self) -> str: return "Rd"

class Const(MnemonicArguments):
    def __init__(self): super().__init__(False, False, True)
    def format(self, i: Instruction) -> str: return str(i.constant) if i.constant else "[const]"
    def parse(self, ib: 'InstructionBuilder', p: 'Parser'): ib.set_constant(p.parse_expression())
    def __str__(self) -> str: return "[const]"

class Brace(MnemonicArguments):
    def __init__(self, inner: MnemonicArguments):
        super().__init__(inner.has_source, inner.has_dest, inner.has_const)
        self.inner = inner
    def format(self, i: Instruction) -> str: return f"[{self.inner.format(i)}]"
    def parse(self, ib: 'InstructionBuilder', p: 'Parser'):
        p.consume('[')
        self.inner.parse(ib, p)
        p.consume(']')
    def __str__(self) -> str: return f"[{self.inner}]"

class Concat(MnemonicArguments):
    def __init__(self, before: MnemonicArguments, char: str, after: MnemonicArguments):
        super().__init__(before.has_source or after.has_source,
                         before.has_dest or after.has_dest,
                         before.has_const or after.has_const)
        self.before = before
        self.char = char
        self.after = after
    def format(self, i: Instruction) -> str: return f"{self.before.format(i)}{self.char}{self.after.format(i)}"
    def parse(self, ib: 'InstructionBuilder', p: 'Parser'):
        self.before.parse(ib, p)
        p.consume(self.char)
        self.after.parse(ib, p)
    def __str__(self) -> str: return f"{self.before}{self.char}{self.after}"

class Comma(Concat):
    def __init__(self, before: MnemonicArguments, after: MnemonicArguments):
        super().__init__(before, ',', after)

class Plus(Concat):
    # Specifically for Rd+[const] or Rs+[const] patterns inside braces
    def __init__(self, reg_part: MnemonicArguments, const_part: Const):
        if not isinstance(const_part, Const):
            raise TypeError("Second part of Plus must be Const")
        if not (reg_part.has_dest ^ reg_part.has_source): # Must be exactly one reg
             raise TypeError("First part of Plus must be Dest or Source")

        # The constant parsed here acts as the main constant for the instruction
        super().__init__(reg_part, '+', const_part)

    def parse(self, ib: 'InstructionBuilder', p: 'Parser'):
        self.before.parse(ib, p) # Parse the Rd or Rs part
        if p.is_next('-'):
            p.consume('-') # Consume the '-'
            self.after.parse(ib, p) # Parse the constant expression
            ib.neg_constant() # Negate the constant stored in the builder
        elif p.is_next('+'):
            p.consume('+') # Consume the '+'
            self.after.parse(ib, p) # Parse the constant expression
        else:
            # Allow omitting + if constant is directly adjacent e.g. [R1 5] -> [R1+5] implicitly?
            # For now, require explicit + or -
             raise p.make_parser_exception("Expected '+' or '-' after register in address expression")

    def format(self, i: Instruction) -> str:
        # Formatting needs care: constant might be negative.
        const_expr = i.constant
        op_char = '+'
        val_str = str(const_expr) if const_expr else '?'

        # Try to represent negative constants with '-' directly
        # This is tricky because the expression could be complex.
        # Simplest approach: if it looks like a negative constant, format it that way.
        if isinstance(const_expr, Constant):
             try:
                 val = const_expr.get_value(None)
                 if val < 0:
                     op_char = '-'
                     val_str = str(-val)
                 else:
                     val_str = str(val)
             except ExpressionException:
                 pass # Stick with default string if value unavailable
        elif isinstance(const_expr, Neg):
            op_char = '-'
            val_str = str(const_expr.value)

        return f"{self.before.format(i)}{op_char}{val_str}"


# --- Pre-defined instances ---
# These are created once MnemonicArguments and its subclasses are defined.
# They are accessed via the MNEMONIC_ARG_LOOKUP dictionary.
MNEMONIC_ARG_LOOKUP: Dict[str, MnemonicArguments] = {
    'NOTHING': Nothing(),
    'SOURCE': Source(),
    'DEST': Dest(),
    'CONST': Const(),
    'DEST_SOURCE': Comma(Dest(), Source()),
    'DEST_CONST': Comma(Dest(), Const()),
    'BDEST_SOURCE': Comma(Brace(Dest()), Source()), # ST [Rd],Rs
    'DEST_BSOURCE': Comma(Dest(), Brace(Source())), # LD Rd,[Rs]
    'CONST_SOURCE': Comma(Const(), Source()), # STS [const],Rs
    # STD [Rd+[const]],Rs -> Brace(Plus(Dest(), Const())), Source()
    'BDEST_BCONST_SOURCE': Comma(Brace(Plus(Dest(), Const())), Source()),
    # LDD Rd,[Rs+[const]] -> Dest(), Brace(Plus(Source(), Const()))
    'DEST_BSOURCE_BCONST': Comma(Dest(), Brace(Plus(Source(), Const()))),
}

