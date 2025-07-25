from typing import Dict
from assembler.expression import Context, ExpressionException
from .instruction import Instruction
from .instruction_visitor import InstructionVisitor
from .opcode import Opcode, ALUBSel

class OptimizerShort(InstructionVisitor):
    """Tries to replace long constant instructions with short versions."""
    def __init__(self):
        # Map from long-form opcode to short-form opcode
        self._short_constant_map: Dict[Opcode, Opcode] = {
                Opcode.LDI: Opcode.LDIs,
                Opcode.OUT: Opcode.OUTs,
                Opcode.ADDI: Opcode.ADDIs,
                Opcode.ADCI: Opcode.ADCIs,
                Opcode.SUBI: Opcode.SUBIs,
                Opcode.SBCI: Opcode.SBCIs,
                Opcode.ANDI: Opcode.ANDIs,
                Opcode.ORI: Opcode.ORIs,
                Opcode.EORI: Opcode.EORIs,
                Opcode.CPI: Opcode.CPIs,
                Opcode.CPCI: Opcode.CPCIs,
                Opcode.LDS: Opcode.LDSs,
                Opcode.STS: Opcode.STSs,
                Opcode.MULI: Opcode.MULIs,
                Opcode.IN: Opcode.INs,
                }
        self._optimized = False # Track if any change was made

    @property
    def was_optimized(self) -> bool:
        return self._optimized

    def visit(self, instruction: 'InstructionInterface', context: Context) -> bool:
        if isinstance(instruction, Instruction):
            op = instruction.opcode
            op_short = self._short_constant_map.get(op)

            if op_short is not None:
                if instruction.constant is None: return True # Should have constant

                try:
                    con = instruction.constant.get_value(context)
                    # Short instructions use 4-bit unsigned constants (0-15)
                    if 0 <= con <= 15:
                        if instruction.opcode != op_short: # Check if already optimized
                            instruction.opcode = op_short
                            self._optimized = True
                except ExpressionException as e:
                    # If constant cannot be resolved yet, skip optimization
                    # print(f"Warning: Could not resolve constant at line {instruction.line_number}: {e}")
                    pass
        return True
