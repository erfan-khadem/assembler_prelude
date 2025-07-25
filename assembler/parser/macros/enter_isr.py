from assembler.asm import Program, InstructionBuilder, Register, Opcode, MnemonicArguments
from ..macro import Macro
class EnterISR(Macro):
    def __init__(self): from assembler.asm.mnemonic_arguments import MNEMONIC_ARG_LOOKUP; super().__init__("ENTERI", MNEMONIC_ARG_LOOKUP['NOTHING'], "pushes R0 and the flags to the stack")
    def parse_macro(self, p: Program, name: str, parser: 'Parser'):
        from ..parser import Parser
        p.set_pending_macro_description(self.name)
        # STD [SP-1], R0  -- Store R0 first
        p.add(InstructionBuilder(Opcode.STD).set_dest(Register.SP).set_source(Register.R0).set_constant_int(-1).build())
        # IN R0, 0        -- Read flags from IO port 0 into R0
        p.add(InstructionBuilder(Opcode.IN).set_dest(Register.R0).set_constant_int(0).build())
        # STD [SP-2], R0  -- Store flags
        p.add(InstructionBuilder(Opcode.STD).set_dest(Register.SP).set_source(Register.R0).set_constant_int(-2).build())
        # SUBI SP, 2      -- Adjust stack pointer
        p.add(InstructionBuilder(Opcode.SUBIs).set_dest(Register.SP).set_constant_int(2).build())
