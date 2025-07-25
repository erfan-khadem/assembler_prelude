from assembler.asm import Program, InstructionBuilder, Register, Opcode, MnemonicArguments
from ..macro import Macro
class LeaveISR(Macro):
    def __init__(self): from assembler.asm.mnemonic_arguments import MNEMONIC_ARG_LOOKUP; super().__init__("LEAVEI", MNEMONIC_ARG_LOOKUP['NOTHING'], "pops R0 and the flags from the stack")
    def parse_macro(self, p: Program, name: str, parser: 'Parser'):
        from ..parser import Parser
        p.set_pending_macro_description(self.name)
        # ADDI SP, 2       -- Adjust stack pointer first
        p.add(InstructionBuilder(Opcode.ADDIs).set_dest(Register.SP).set_constant_int(2).build())
        # LDD R0, [SP-2]   -- Load flags from stack into R0 (address is now relative to adjusted SP)
        p.add(InstructionBuilder(Opcode.LDD).set_dest(Register.R0).set_source(Register.SP).set_constant_int(-2).build())
        # OUT 0, R0        -- Write flags to IO port 0
        p.add(InstructionBuilder(Opcode.OUT).set_source(Register.R0).set_constant_int(0).build())
        # LDD R0, [SP-1]   -- Load original R0 from stack
        p.add(InstructionBuilder(Opcode.LDD).set_dest(Register.R0).set_source(Register.SP).set_constant_int(-1).build())

