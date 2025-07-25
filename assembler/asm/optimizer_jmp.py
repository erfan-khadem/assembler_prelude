from assembler.expression import Context, ExpressionException
from .instruction import Instruction
from .instruction_visitor import InstructionVisitor
from .opcode import Opcode

class OptimizerJmp(InstructionVisitor):
    """Tries to replace a long JMP by a short JMPs if target is near enough."""
    def __init__(self):
        self._optimized = False

    @property
    def was_optimized(self) -> bool:
        return self._optimized

    def visit(self, instruction: 'InstructionInterface', context: Context) -> bool:
        if isinstance(instruction, Instruction):
            op = instruction.opcode
            if op == Opcode.JMP:
                if instruction.constant is None: return True # Should not happen if built correctly

                try:
                    con = instruction.constant.get_value(context)
                    # Offset = TargetAddr - CurrentAddr - 1 (for relative jump)
                    ofs = con - context.instr_addr - 1
                    # JMPs uses 8-bit signed offset (-128 to 127)
                    if -128 <= ofs <= 127:
                        instruction.opcode = Opcode.JMPs
                        # We need to indicate that an optimization happened,
                        # but also stop traversal for this instruction
                        # as its size might change implicitly in the next pass.
                        # The Program's optimization loop handles re-traversal.
                        self._optimized = True
                        # Return True to continue traversal, Program loop handles iteration
                except ExpressionException as e:
                     # If constant cannot be resolved yet, skip optimization
                     # print(f"Warning: Could not resolve JMP target at line {instruction.line_number}: {e}")
                     pass
        return True


