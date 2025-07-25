import pytest
from assembler.asm import (
    InstructionBuilder, Opcode, Register, InstructionException, Program, MachineCodeListener
)
from assembler.expression import ExpressionException, Context, Constant

class MockMachineCodeListener(MachineCodeListener):
    def __init__(self):
        self.code = []
    def add(self, instr: int):
        self.code.append(instr)

def test_constant_ldss():
    mc = MockMachineCodeListener()
    # Valid short constant (0-15)
    InstructionBuilder(Opcode.LDSs).set_dest(Register.R0).set_constant_int(15).build().create_machine_code(Context(), mc)
    assert len(mc.code) == 1

    mc = MockMachineCodeListener()
    with pytest.raises(ExpressionException, match="short constant too large"):
        InstructionBuilder(Opcode.LDSs).set_dest(Register.R0).set_constant_int(16).build().create_machine_code(Context(), mc)

    mc = MockMachineCodeListener()
    with pytest.raises(ExpressionException, match="short constant too large"):
         # Negative numbers are invalid for unsigned short constants
        InstructionBuilder(Opcode.LDSs).set_dest(Register.R0).set_constant_int(-1).build().create_machine_code(Context(), mc)

def test_constant_stss():
    mc = MockMachineCodeListener()
    # Valid short constant (0-15) for address
    InstructionBuilder(Opcode.STSs).set_source(Register.R0).set_constant_int(15).build().create_machine_code(Context(), mc)
    assert len(mc.code) == 1

    mc = MockMachineCodeListener()
    with pytest.raises(ExpressionException, match="short constant too large"):
        InstructionBuilder(Opcode.STSs).set_source(Register.R0).set_constant_int(16).build().create_machine_code(Context(), mc)

    mc = MockMachineCodeListener()
    with pytest.raises(ExpressionException, match="short constant too large"):
        InstructionBuilder(Opcode.STSs).set_source(Register.R0).set_constant_int(-1).build().create_machine_code(Context(), mc)

def test_jmps_branch_range():
    mc = MockMachineCodeListener()
    ctx = Context().set_instr_addr(1000)

    # Target = Addr + 1 + Offset => Offset = Target - Addr - 1
    # Max positive offset: 127 => Target = 1000 + 1 + 127 = 1128
    InstructionBuilder(Opcode.JMPs).set_constant(Constant(1128)).build().create_machine_code(ctx, mc)
    mc = MockMachineCodeListener()
    with pytest.raises(ExpressionException, match="branch target out of range"):
        # Offset 128
        InstructionBuilder(Opcode.JMPs).set_constant(Constant(1129)).build().create_machine_code(ctx, mc)

    mc = MockMachineCodeListener()
    # Min negative offset: -128 => Target = 1000 + 1 - 128 = 873
    InstructionBuilder(Opcode.JMPs).set_constant(Constant(873)).build().create_machine_code(ctx, mc)
    mc = MockMachineCodeListener()
    with pytest.raises(ExpressionException, match="branch target out of range"):
        # Offset -129
        InstructionBuilder(Opcode.JMPs).set_constant(Constant(872)).build().create_machine_code(ctx, mc)
