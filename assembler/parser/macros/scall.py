from assembler.asm import Program, InstructionBuilder, Register, Opcode, MnemonicArguments
from ..macro import Macro
from .push import push_instruction
from .pop import pop_instruction
class SCall(Macro):
    def __init__(self): from assembler.asm.mnemonic_arguments import MNEMONIC_ARG_LOOKUP; super().__init__("_SCALL", MNEMONIC_ARG_LOOKUP['CONST'], "jumps to the address given in const and stores the return address in the register RA. Before that RA ist pushed to the stack, and after the return RA is poped of the stack again.")
    def parse_macro(self, p: Program, name: str, parser: 'Parser'):
        from ..parser import Parser
        addr = parser.parse_expression(); p.set_pending_macro_description(f"{self.name} {addr}")
        push_instruction(Register.RA, p)
        p.add(InstructionBuilder(Opcode.RCALL).set_dest(Register.RA).set_constant(addr).build())
        pop_instruction(Register.RA, p)
