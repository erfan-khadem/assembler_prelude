import pytest
import io
from assembler.parser import Parser
from assembler.asm import Program, Opcode, Register, Instruction

def parse_macro_prog(code: str) -> Program:
     # Don't link, just parse to check expansion
     return Parser(code).parse_program()

def test_call():
    prog = parse_macro_prog("call target")
    assert prog.instruction_count == 4
    assert prog.get_instruction(0).opcode == Opcode.SUBIs
    assert prog.get_instruction(0).dest_reg == Register.SP
    assert prog.get_instruction(1).opcode == Opcode.LDI
    assert prog.get_instruction(1).dest_reg == Register.RA
    # Constant should be _SKIP2_ADDR_ identifier
    assert prog.get_instruction(2).opcode == Opcode.ST
    assert prog.get_instruction(3).opcode == Opcode.JMP
    assert str(prog.get_instruction(3).constant) == "target"

def test_dec():
    prog = parse_macro_prog("dec r0")
    assert prog.instruction_count == 1
    instr = prog.get_instruction(0)
    assert instr.opcode == Opcode.SUBIs
    assert instr.dest_reg == Register.R0
    assert instr.constant.get_value(None) == 1

def test_inc():
    prog = parse_macro_prog("inc r0")
    assert prog.instruction_count == 1
    instr = prog.get_instruction(0)
    assert instr.opcode == Opcode.ADDIs
    assert instr.dest_reg == Register.R0
    assert instr.constant.get_value(None) == 1

def test_enter():
    prog = parse_macro_prog("enter 1")
    assert prog.instruction_count == 4 # PUSH BP (2) + MOV + SUBI
    assert prog.get_instruction(0).opcode == Opcode.SUBIs # push bp
    assert prog.get_instruction(1).opcode == Opcode.ST # push bp
    assert prog.get_instruction(2).opcode == Opcode.MOV
    assert prog.get_instruction(3).opcode == Opcode.SUBI
    assert prog.get_instruction(3).constant.get_value(None) == 1

def test_enter_zero():
     prog = parse_macro_prog("enter 0")
     assert prog.instruction_count == 3 # PUSH BP (2) + MOV (SUBI is skipped)
     assert prog.get_instruction(2).opcode == Opcode.MOV

def test_leave():
    prog = parse_macro_prog("leave")
    assert prog.instruction_count == 3 # MOV + POP BP (2)
    assert prog.get_instruction(0).opcode == Opcode.MOV
    assert prog.get_instruction(1).opcode == Opcode.LD # pop bp
    assert prog.get_instruction(2).opcode == Opcode.ADDIs # pop bp

def test_pop():
    prog = parse_macro_prog("pop r0")
    assert prog.instruction_count == 2
    assert prog.get_instruction(0).opcode == Opcode.LD
    assert prog.get_instruction(1).opcode == Opcode.ADDIs

def test_push():
    prog = parse_macro_prog("push r0")
    assert prog.instruction_count == 2
    assert prog.get_instruction(0).opcode == Opcode.SUBIs
    assert prog.get_instruction(1).opcode == Opcode.ST

def test_ret():
    prog = parse_macro_prog("ret") # POP RA (2) + RRET RA
    assert prog.instruction_count == 3
    assert prog.get_instruction(0).opcode == Opcode.LD
    assert prog.get_instruction(1).opcode == Opcode.ADDIs
    assert prog.get_instruction(2).opcode == Opcode.RRET

def test_ret_const():
    prog = parse_macro_prog("ret 3") # LD RA + ADDI SP, 3+1 + RRET RA
    assert prog.instruction_count == 3
    assert prog.get_instruction(0).opcode == Opcode.LD
    assert prog.get_instruction(1).opcode == Opcode.ADDI # Uses long ADDI
    assert prog.get_instruction(1).constant.get_value(None) == 4
    assert prog.get_instruction(2).opcode == Opcode.RRET

def test_scall():
    prog = parse_macro_prog("_scall target") # PUSH RA (2) + RCALL + POP RA (2)
    assert prog.instruction_count == 5
    assert prog.get_instruction(0).opcode == Opcode.SUBIs # push
    assert prog.get_instruction(1).opcode == Opcode.ST    # push
    assert prog.get_instruction(2).opcode == Opcode.RCALL
    assert str(prog.get_instruction(2).constant) == "target"
    assert prog.get_instruction(3).opcode == Opcode.LD    # pop
    assert prog.get_instruction(4).opcode == Opcode.ADDIs # pop

def test_enteri():
     prog = parse_macro_prog("enteri")
     # STD [SP-1],R0; IN R0,0; STD [SP-2],R0; SUBIs SP,2
     assert prog.instruction_count == 4
     assert prog.get_instruction(0).opcode == Opcode.STD
     assert prog.get_instruction(1).opcode == Opcode.IN
     assert prog.get_instruction(2).opcode == Opcode.STD
     assert prog.get_instruction(3).opcode == Opcode.SUBIs

def test_leavei():
     prog = parse_macro_prog("leavei")
     # ADDIs SP,2; LDD R0,[SP-2]; OUT 0,R0; LDD R0,[SP-1]
     assert prog.instruction_count == 4
     assert prog.get_instruction(0).opcode == Opcode.ADDIs
     assert prog.get_instruction(1).opcode == Opcode.LDD
     assert prog.get_instruction(2).opcode == Opcode.OUT
     assert prog.get_instruction(3).opcode == Opcode.LDD

# ... Add test_include.py, test_branch.py, etc. Need resource files for include.

# --- Example Usage ---