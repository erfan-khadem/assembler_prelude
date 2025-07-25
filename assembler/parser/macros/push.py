import io
from assembler.asm import Program, InstructionBuilder, Register, Opcode, InstructionException, MnemonicArguments
from assembler.expression import ExpressionException, Constant
from ..macro import Macro
from ..parser_exception import ParserException

def push_instruction(reg: Register, p: Program):
    """Helper function to generate PUSH instructions."""
    p.add(InstructionBuilder(Opcode.SUBIs).set_dest(Register.SP).set_constant_int(1).build())
    p.add(InstructionBuilder(Opcode.ST).set_dest(Register.SP).set_source(reg).build())

class Push(Macro):
    def __init__(self):
        # Need MnemonicArguments instance here
        from assembler.asm.mnemonic_arguments import MNEMONIC_ARG_LOOKUP
        super().__init__("PUSH", MNEMONIC_ARG_LOOKUP['SOURCE'],
                         "copies the value in the given register to the stack, decreases the stack pointer by one")

    def parse_macro(self, p: Program, name: str, parser: 'Parser'):
        from ..parser import Parser # Use '..' for relative import within package
        reg = parser.parse_reg()
        p.set_pending_macro_description(f"{self.name} {reg.name}")
        push_instruction(reg, p)

# (Create similar files for Pop, Call, Ret, Inc, Dec, Enter, Leave, SCall, EnterISR, LeaveISR)
