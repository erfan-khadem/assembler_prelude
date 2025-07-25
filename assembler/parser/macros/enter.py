from assembler.asm import Program, InstructionBuilder, Register, Opcode, MnemonicArguments
from assembler.expression import Expression, Constant
from ..macro import Macro
from .push import push_instruction
class Enter(Macro):
    def __init__(self): from assembler.asm.mnemonic_arguments import MNEMONIC_ARG_LOOKUP; super().__init__("ENTER", MNEMONIC_ARG_LOOKUP['CONST'], "pushes BP on stack, copies SP to BP and reduces SP by the given constant")
    def parse_macro(self, p: Program, name: str, parser: 'Parser'):
        from ..parser import Parser
        size = parser.parse_expression(); p.set_pending_macro_description(f"{self.name} {size}")
        push_instruction(Register.BP, p)
        p.add(InstructionBuilder(Opcode.MOV).set_dest(Register.BP).set_source(Register.SP).build())
        is_zero = False
        if isinstance(size, Constant):
            try: is_zero = (size.get_value(None) == 0)
            except: pass
        if not is_zero:
            p.add(InstructionBuilder(Opcode.SUBI).set_dest(Register.SP).set_constant(size).build())
