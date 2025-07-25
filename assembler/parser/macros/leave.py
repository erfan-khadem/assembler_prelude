from assembler.asm import Program, InstructionBuilder, Register, Opcode, MnemonicArguments
from ..macro import Macro
from .pop import pop_instruction
class Leave(Macro):
    def __init__(self): from assembler.asm.mnemonic_arguments import MNEMONIC_ARG_LOOKUP; super().__init__("LEAVE", MNEMONIC_ARG_LOOKUP['NOTHING'], "moves BP to SP and pops BP from the stack")
    def parse_macro(self, p: Program, name: str, parser: 'Parser'):
        from ..parser import Parser
        p.set_pending_macro_description(self.name)
        p.add(InstructionBuilder(Opcode.MOV).set_dest(Register.SP).set_source(Register.BP).build())
        pop_instruction(Register.BP, p)
