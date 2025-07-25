from assembler.asm import Program, InstructionBuilder, Register, Opcode, MnemonicArguments, Context
from assembler.expression import Identifier
from ..macro import Macro

class Call(Macro):
    def __init__(self):
        from assembler.asm.mnemonic_arguments import MNEMONIC_ARG_LOOKUP
        super().__init__("CALL", MNEMONIC_ARG_LOOKUP['CONST'], "Jumps to the given Address, stores the return address on the stack.")

    def parse_macro(self, p: Program, name: str, parser: 'Parser'):
        from ..parser import Parser
        # Logic based on Java Call.java
        addr = parser.parse_expression()
        p.set_pending_macro_description(f"{self.name} {addr}")
        # 1. Make space on stack: SUBIs SP, 1
        p.add(InstructionBuilder(Opcode.SUBIs).set_dest(Register.SP).set_constant_int(1).build())
        # 2. Load return address into RA: LDI RA, _SKIP2_ADDR_
        #    _SKIP2_ADDR_ points to the instruction *after* the JMP that follows this macro expansion.
        p.add(InstructionBuilder(Opcode.LDI).set_dest(Register.RA).set_constant(Identifier(Context.SKIP2_ADDR)).build())
        # 3. Store RA onto stack: ST [SP], RA
        p.add(InstructionBuilder(Opcode.ST).set_dest(Register.SP).set_source(Register.RA).build())
        # 4. Jump to target: JMP addr
        p.add(InstructionBuilder(Opcode.JMP).set_constant(addr).build())
