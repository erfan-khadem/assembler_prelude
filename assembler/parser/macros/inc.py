from assembler.asm import Program, InstructionBuilder, Register, Opcode, InstructionException, MnemonicArguments
from ..macro import Macro
class Inc(Macro):
    def __init__(self): from assembler.asm.mnemonic_arguments import MNEMONIC_ARG_LOOKUP; super().__init__("INC", MNEMONIC_ARG_LOOKUP['DEST'], "increases the given register by one")
    def parse_macro(self, p: Program, name: str, parser: 'Parser'):
        from ..parser import Parser
        r = parser.parse_reg(); p.set_pending_macro_description(f"{self.name} {r.name}"); p.add(InstructionBuilder(Opcode.ADDIs).set_dest(r).set_constant_int(1).build())
