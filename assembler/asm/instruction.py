from typing import Optional
from assembler.expression import Expression, Context, ExpressionException, Constant
from .register import Register
from .opcode import Opcode, ALUBSel, ImmExtMode
from .instruction_interface import InstructionInterface
from .machine_code_listener import MachineCodeListener

class Instruction(InstructionInterface):
    """Represents a standard machine instruction."""

    def __init__(self, opcode: Opcode, dest_reg: Register, source_reg: Register, constant: Optional[Expression]):
        self._opcode = opcode
        self._dest_reg = dest_reg
        self._source_reg = source_reg
        self._constant = constant
        self._label: Optional[str] = None
        self._macro_description: Optional[str] = None
        self._comment: Optional[str] = None
        self._line_number: int = 0
        self._abs_addr: int = -1

    @property
    def size(self) -> int:
        # Instructions using ImReg take two words (opcode word + constant word)
        return 2 if self._opcode.alu_b_sel == ALUBSel.ImReg else 1

    def set_line_number(self, line_number: int) -> 'Instruction':
        self._line_number = line_number
        return self

    @property
    def line_number(self) -> int:
        return self._line_number

    @property
    def label(self) -> Optional[str]:
        return self._label

    @label.setter
    def label(self, value: Optional[str]):
        self._label = value

    @property
    def macro_description(self) -> Optional[str]:
        return self._macro_description

    @macro_description.setter
    def macro_description(self, value: Optional[str]):
        self._macro_description = value

    @property
    def comment(self) -> Optional[str]:
        return self._comment

    @comment.setter
    def comment(self, value: Optional[str]):
        self._comment = value

    @property
    def abs_addr(self) -> int:
        return self._abs_addr

    @abs_addr.setter
    def abs_addr(self, value: int):
        self._abs_addr = value

    @property
    def opcode(self) -> Opcode:
        return self._opcode

    @opcode.setter
    def opcode(self, value: Opcode):
         self._opcode = value

    @property
    def source_reg(self) -> Register:
        return self._source_reg

    @property
    def dest_reg(self) -> Register:
        return self._dest_reg

    @property
    def constant(self) -> Optional[Expression]:
        return self._constant

    def _is_const_invalid(self, value: int, bits: int, signed: bool) -> bool:
        """Checks if a constant value fits within the specified bit width."""
        if signed:
            min_val = -(1 << (bits - 1))
            max_val = (1 << (bits - 1)) - 1
            return not (min_val <= value <= max_val)
        else:
            min_val = 0
            max_val = (1 << bits) - 1
            return not (min_val <= value <= max_val)

    def create_machine_code(self, context: Context, mc: MachineCodeListener):
        try:
            con = 0
            if self._constant is not None:
                con = self._constant.get_value(context)

            # Default encoding: opcode | dest << 4 | source
            mcode = self._source_reg.value | (self._dest_reg.value << 4)

            alu_b_sel = self._opcode.alu_b_sel

            if alu_b_sel == ALUBSel.instrSourceAndDest:
                # Branch instructions: constant is relative offset
                # Offset = TargetAddr - CurrentAddr - 1
                ofs = con - context.instr_addr - 1
                if self._is_const_invalid(ofs, 8, True): # 8-bit signed offset
                    raise ExpressionException(f"branch target out of range ({ofs})")
                mcode = ofs & 0xFF # Use lower 8 bits for offset

            elif alu_b_sel == ALUBSel.instrSource:
                # Short immediate (dest holds low nibble const): Rd << 4 | const
                if self._is_const_invalid(con, 4, False): # 4-bit unsigned const
                    raise ExpressionException(f"short constant too large ({con})")
                mcode = (con & 0xF) | (self._dest_reg.value << 4)

            elif alu_b_sel == ALUBSel.instrDest:
                 # Short immediate (source holds low nibble const): const << 4 | Rs
                if self._is_const_invalid(con, 4, False): # 4-bit unsigned const
                    raise ExpressionException(f"short constant too large ({con})")
                mcode = self._source_reg.value | ((con & 0xF) << 4)

            elif alu_b_sel == ALUBSel.ImReg:
                # Two-word instruction: emit constant first, then opcode word
                # Constant word format: 1_cccccccccccccc (15 bits value)
                # Check limits based on ImmExtMode
                imm_ext = self._opcode.imm_ext_mode
                const_bit = 0

                if imm_ext == ImmExtMode.extend: # e.g., LDD, STD (signed displacement)
                    if self._is_const_invalid(con, 15, True):
                        raise ExpressionException(f"displacement constant too large ({con})")
                else: # e.g., LDI, ADDI (unsigned or handled differently)
                     # Check if fits in 16 bits initially, specific checks below
                     if self._is_const_invalid(con, 16, False): # Allow full 16-bit range for immediate ops initially
                        # Allow signed 16 bit for now as well
                        if self._is_const_invalid(con, 16, True):
                           raise ExpressionException(f"constant out of 16-bit range ({con})")

                # Emit the constant word (lower 15 bits + high bit marker)
                mc.add((con & 0x7FFF) | 0x8000)

                # Determine the 'constBit' for the opcode word based on the 16th bit (sign for extend?)
                if (con & 0x8000) != 0:
                     const_bit = 1

                # Modify opcode word based on ImmExtMode
                if imm_ext == ImmExtMode.src0: # Constant effectively replaces source reg operand
                    # Opcode word: Op | Rd << 4 | constBit
                    mcode = const_bit | (self._dest_reg.value << 4)
                elif imm_ext == ImmExtMode.dest0: # Constant effectively replaces dest reg operand
                    # Opcode word: Op | constBit << 4 | Rs
                    mcode = self._source_reg.value | (const_bit << 4)
                # else: ImmExtMode.extend uses default mcode (Rd/Rs for addressing)

            # Combine with opcode value (shifted to high byte)
            # Enum members have implicit 'value' which is their ordinal position
            mcode |= (self._opcode.value << 8)
            mc.add(mcode)

        except ExpressionException as e:
            e.set_line_number(self._line_number)
            raise e
        except Exception as e:
             # Wrap other potential errors
             new_e = ExpressionException(f"Error during machine code generation: {e}")
             new_e.set_line_number(self._line_number)
             raise new_e from e


    def __str__(self) -> str:
        s = ""
        if self._label:
            s += f"{self._label}:"
        # Add padding if label exists
        s = f"{s:<9}" if self._label else " " * 9

        s += f"{self._opcode.name:<6} " # Pad opcode name
        try:
            # Need MnemonicArguments to format correctly
            from .mnemonic_arguments import MnemonicArguments
            args_str = self._opcode.arguments.format(self)
            s += args_str
        except Exception: # If formatting fails (e.g., during init)
            s += "<error formatting args>"

        if self._constant is not None and self._opcode.arguments.has_const:
             try:
                  # Try to get value if possible (may fail if context missing)
                  const_val_str = f" ; 0x{self._constant.get_value(None) & 0xFFFF:x}" \
                                  if isinstance(self._constant, Constant) else ""
                  s += f"{const_val_str}"
             except:
                  pass # Ignore if value cannot be resolved yet

        return s.rstrip() # Remove trailing space if no const comment


    def __repr__(self) -> str:
        return (f"Instruction(opcode={self._opcode.name}, dest={self._dest_reg.name}, "
                f"source={self._source_reg.name}, const={repr(self._constant)}, "
                f"label={self._label}, line={self._line_number})")


