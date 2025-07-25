from assembler.asm import Program, InstructionBuilder, Register, Opcode, MnemonicArguments
from assembler.expression import Expression, Constant, Operate, Operation
from ..macro import Macro
from .pop import pop_instruction
class Ret(Macro):
    def __init__(self): from assembler.asm.mnemonic_arguments import MNEMONIC_ARG_LOOKUP; super().__init__("RET", MNEMONIC_ARG_LOOKUP['CONST'], "jumps to the address which is stored on top of the stack. decreases the stack pointer by 1+const. const is optional")
    def parse_macro(self, p: Program, name: str, parser: 'Parser'):
        from ..parser import Parser
        size: Expression | None = None
        if not parser.is_eol():
            size = parser.parse_expression()
            p.set_pending_macro_description(f"{self.name} {size}")
            p.add(InstructionBuilder(Opcode.LD).set_dest(Register.RA).set_source(Register.SP).build()) # Load return addr
            # Add 1 + const to SP
            final_size = Operate(size, Operation.ADD, Constant(1))
            p.add(InstructionBuilder(Opcode.ADDI).set_dest(Register.SP).set_constant(final_size).build())
        else:
            p.set_pending_macro_description(self.name)
            pop_instruction(Register.RA, p) # Standard pop adjusts SP by 1

        p.add(InstructionBuilder(Opcode.RRET).set_source(Register.RA).build()) # Jump to address in RA
