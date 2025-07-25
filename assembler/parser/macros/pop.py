import io
from assembler.asm import Program, InstructionBuilder, Register, Opcode, InstructionException, MnemonicArguments
from assembler.expression import ExpressionException, Constant
from ..macro import Macro
from ..parser_exception import ParserException

def pop_instruction(reg: Register, p: Program):
    """Helper function to generate POP instructions."""
    p.add(InstructionBuilder(Opcode.LD).set_dest(reg).set_source(Register.SP).build())
    p.add(InstructionBuilder(Opcode.ADDIs).set_dest(Register.SP).set_constant_int(1).build())

class Pop(Macro):
    def __init__(self):
        from assembler.asm.mnemonic_arguments import MNEMONIC_ARG_LOOKUP
        super().__init__("POP", MNEMONIC_ARG_LOOKUP['DEST'],
                         "copy value from the stack to the given register, adds one to the stack pointer")

    def parse_macro(self, p: Program, name: str, parser: 'Parser'):
        from ..parser import Parser
        reg = parser.parse_reg()
        p.set_pending_macro_description(f"{self.name} {reg.name}")
        pop_instruction(reg, p)

# ... Create all other macro files similarly ...
