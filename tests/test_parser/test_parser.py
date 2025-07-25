import pytest
import io
from assembler.parser import Parser, ParserException
from assembler.asm import Program, Opcode, Register, Instruction, InstructionInterface
from assembler.expression import Context, ExpressionException, Constant, Identifier, Operate, Operation

# Helper function to parse code and return the program string
def parse_to_string(code: str) -> str:
    prog = Parser(code).parse_program()
    # Use io.StringIO to capture the output of AsmFormatter
    out = io.StringIO()
    # Need a context for formatting potentially complex expressions
    ctx = Context()
    try:
        # Try linking to resolve labels for formatting
        prog = prog.optimize_and_link()
        prog.traverse(lambda i,c: True) # Run traversal to populate context if needed
    except Exception:
        pass # Ignore linking errors for basic parse tests

    # Now format using the (potentially updated) context
    from assembler.asm.formatters import AsmFormatter
    formatter = AsmFormatter(out, include_line_numbers=False)
    prog.traverse(formatter)
    return out.getvalue()

def test_simple_mov():
    prog = Parser("MOV R0,R1").parse_program()
    assert prog.instruction_count == 1
    instr = prog.get_instruction(0)
    assert isinstance(instr, Instruction)
    assert instr.opcode == Opcode.MOV
    assert instr.dest_reg == Register.R0
    assert instr.source_reg == Register.R1
    assert instr.label is None

def test_simple_mov_comment():
    prog = Parser("MOV R0,R1 ; Testcomment").parse_program()
    assert prog.instruction_count == 1
    instr = prog.get_instruction(0)
    assert isinstance(instr, Instruction)
    assert instr.opcode == Opcode.MOV
    assert instr.comment == "; Testcomment" # Check if parser attaches comments

def test_simple_mov_label():
    prog = Parser("test: MOV R0,R1").parse_program()
    assert prog.instruction_count == 1
    instr = prog.get_instruction(0)
    assert isinstance(instr, Instruction)
    assert instr.opcode == Opcode.MOV
    assert instr.label == "test"

def test_simple_two_commands():
    prog = Parser("MOV R0,R1\nMOV R2,R3").parse_program()
    assert prog.instruction_count == 2
    i0 = prog.get_instruction(0)
    i1 = prog.get_instruction(1)
    assert i0.opcode == Opcode.MOV and i0.dest_reg == Register.R0 and i0.source_reg == Register.R1
    assert i1.opcode == Opcode.MOV and i1.dest_reg == Register.R2 and i1.source_reg == Register.R3

def test_constant_jmp():
    prog = Parser("JMP 12").parse_program()
    instr = prog.get_instruction(0)
    assert instr.opcode == Opcode.JMP
    assert isinstance(instr.constant, Constant)
    assert instr.constant.get_value(None) == 12

    prog = Parser("JMP 2*6").parse_program()
    instr = prog.get_instruction(0)
    assert instr.opcode == Opcode.JMP
    assert isinstance(instr.constant, Operate)
    assert instr.constant.get_value(Context()) == 12 # Need context if expression complex

def test_ldi():
    prog = Parser("LDI R0,5").parse_program()
    instr = prog.get_instruction(0)
    assert instr.opcode == Opcode.LDI
    assert isinstance(instr.constant, Constant)
    assert instr.constant.get_value(None) == 5

def test_macro_inc():
    prog = Parser("INC R5").parse_program()
    # Macro expands to ADDIs R5, 1
    assert prog.instruction_count == 1
    instr = prog.get_instruction(0)
    assert instr.opcode == Opcode.ADDIs
    assert instr.dest_reg == Register.R5
    assert isinstance(instr.constant, Constant)
    assert instr.constant.get_value(None) == 1
    assert instr.macro_description == "INC R5"

def test_directive_word():
    prog = Parser(".word A\n.word b").parse_program()
    ctx = prog.context
    assert ctx.get("A") == 0
    assert ctx.get("b") == 1

def test_directive_words():
     prog = Parser(".word a\n.words b 10\n.word c").parse_program()
     ctx = prog.context
     assert ctx.get("a") == 0
     assert ctx.get("b") == 1
     assert ctx.get("c") == 11 # b reserves 10 words (addr 1 to 10), c starts at 11

def test_directive_long():
    prog = Parser(".long A\n.long b").parse_program()
    ctx = prog.context
    assert ctx.get("A") == 0
    assert ctx.get("b") == 2

def test_directive_const():
    prog = Parser(".const A 2\n.const b A*2+1").parse_program()
    ctx = prog.context
    assert ctx.get("A") == 2
    assert ctx.get("b") == 5

def test_label_case_insensitivity_linking():
    # Should raise ExpressionException during linking if labels clash case-insensitively
    # The parser allows defining them, linking should fail.
    # Java code allows this, Python should too unless context modified.
    # Let's check context behavior more directly
    prog = Parser("L1: mov r0,r1\nl1: mov r0,r1").parse_program()
    with pytest.raises(ExpressionException):
         prog.optimize_and_link() # Linking should detect duplicate label

def test_self_jmp_optimize():
     # JMP should optimize to JMPs
     prog = Parser("end: jmp end").parse_program().optimize_and_link()
     assert prog.instruction_count == 1
     instr = prog.get_instruction(0)
     assert instr.opcode == Opcode.JMPs
     assert instr.constant.get_value(prog.context) == 0

def test_data_addr_harvard():
     prog = Parser(".data test \"Test\",0\n.data test2 \"Test\",0\njmp _ADDR_").parse_program()
     # In Harvard mode, .data allocates RAM and generates load code.
     # Program structure changes significantly. Test optimize_and_link result.
     prog.optimize_and_link()
     ctx = prog.context
     assert ctx.get("test") == 0 # RAM address
     assert ctx.get("test2") == 5 # RAM address
     # Check last instruction is JMP to its own address
     last_instr = prog.get_instruction(prog.instruction_count - 1)
     assert last_instr.opcode == Opcode.JMPs # Optimized jump

def test_ret_macro():
    prog1 = Parser("RET").parse_program().optimize_and_link()
    assert prog1.instruction_count == 3
    assert prog1.get_instruction(1).opcode == Opcode.ADDIs # Pop uses ADDIs
    assert prog1.get_instruction(1).constant.get_value(None) == 1

    prog2 = Parser("RET 2").parse_program().optimize_and_link()
    # Expands to LD RA,[SP]; ADDI SP, 2+1; RRET RA
    # ADDI SP, 3 should be optimized to ADDIs SP, 3
    assert prog2.instruction_count == 3
    assert prog2.get_instruction(1).opcode == Opcode.ADDIs # Expect optimized version
    assert prog2.get_instruction(1).constant.get_value(None) == 3 # Constant is 2+1=3 (Optimized to 3 directly)

def test_address_plus_minus():
    prog = Parser("LDD R0,[R1+5]").parse_program().optimize_and_link()
    assert prog.get_instruction(0).constant.get_value(None) == 5

    prog = Parser("LDD R0,[R1-5]").parse_program().optimize_and_link()
    assert prog.get_instruction(0).constant.get_value(None) == -5

# ... Add more tests for directives, macros, error cases ...
