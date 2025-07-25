import sys
from typing import TextIO, Dict, List
from assembler.expression import Context, ExpressionException
from assembler.asm.instruction_interface import InstructionInterface
from assembler.asm.instruction_visitor import InstructionVisitor
from assembler.asm.machine_code_listener import MachineCodeListener

class HexFormatter(InstructionVisitor):
    """Formats the program into Logisim-compatible hex format."""

    def __init__(self, out: TextIO = sys.stdout):
        self._out = out
        self._addr = 0
        self._output_buffer: Dict[int, int] = {} # Buffer output to handle .org gaps
        self._max_addr = -1

    def visit(self, instr: InstructionInterface, context: Context) -> bool:
        instr_addr = context.instr_addr

        class CodeCollector(MachineCodeListener):
            def __init__(self, buffer: Dict[int, int], start_addr: int):
                self.buffer = buffer
                self.current_addr = start_addr
                self.max_addr = start_addr -1

            def add(self, code: int):
                self.buffer[self.current_addr] = code & 0xFFFF # Ensure 16-bit
                self.max_addr = max(self.max_addr, self.current_addr)
                self.current_addr += 1

        collector = CodeCollector(self._output_buffer, instr_addr)
        try:
            instr.create_machine_code(context, collector)
            self._max_addr = max(self._max_addr, collector.max_addr)
        except ExpressionException as e:
             # Re-raise exception to stop processing, include line number
             e.set_line_number(instr.line_number)
             print(f"\nError generating hex: {e}", file=sys.stderr)
             raise e
        return True

    def finalize(self):
        """Writes the buffered output to the stream, filling gaps with 0."""
        print("v2.0 raw", file=self._out)
        if not self._output_buffer:
            return # Empty program

        # Determine the actual highest address used + 1
        program_size = self._max_addr + 1

        for addr in range(program_size):
            code = self._output_buffer.get(addr, 0) # Default to 0 for gaps
            print(f"{code:x}", file=self._out)
