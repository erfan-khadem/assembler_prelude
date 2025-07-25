import io
from typing import List, Optional, Dict, Tuple, Set
from collections import defaultdict, OrderedDict
import os

from assembler.expression import Context, ExpressionException, Constant
from .instruction import Instruction
from .data_instruction import DataInstruction
from .instruction_interface import InstructionInterface
from .instruction_builder import InstructionBuilder
from .instruction_visitor import InstructionVisitor
from .instruction_exception import InstructionException
from .optimizer_jmp import OptimizerJmp
from .optimizer_short import OptimizerShort
from .opcode import Opcode
from .register import Register

class PendingString:
    """Helper to manage labels/comments added before the instruction."""
    def __init__(self, name: str):
        self.name = name
        self.str_val: Optional[str] = None

    def set(self, s: str):
        if self.str_val is not None:
            # Allow appending comments, but not overwriting labels/macros
            if self.name == "comment":
                 self.str_val += "\n" + s
            else:
                raise ExpressionException(f"Two {self.name}s for the same command: {self.str_val}, {s}")
        else:
            self.str_val = s

    def add(self, s: str):
        """Appends to the string, primarily for comments."""
        if self.str_val is None:
            self.str_val = s
        else:
            self.str_val += s # Or potentially add a newline separator?

    def get(self) -> Optional[str]:
        s = self.str_val
        self.str_val = None # Consume the value
        return s

class Program:
    """Represents an entire assembly program."""

    def __init__(self):
        self._prog: List[InstructionInterface] = []
        self._context = Context()
        # For Harvard arch: data values mapped to list of RAM addresses
        self._data_map: Dict[int, List[int]] = defaultdict(list)
        self._ram_pos: int = 0
        self._pending_label = PendingString("label")
        self._pending_macro_desc = PendingString("description")
        self._pending_comment = PendingString("comment")
        self._current_line_number: int = 0
        self._pending_addr: int = -1
        self._addr_to_line_map: Dict[int, int] = {}
        self._von_neumann: bool = False
        self._ram_start_address: int = 0 # Address where data starts in Von Neumann


    def add_pending_comment(self, comment: str):
        # Allow multiple comments to accumulate, separated by newline
        current = self._pending_comment.get() # Use get to consume previous if any
        new_comment = comment.strip()
        if current:
            # Store consumed value back before appending
            self._pending_comment.set(current + "\n" + new_comment)
        else:
            self._pending_comment.set(new_comment)


    def set_line_number(self, line_number: int):
        self._current_line_number = line_number

    def add(self, i: Instruction):
        """Adds a standard instruction to the program."""
        i.label = self._pending_label.get()
        i.macro_description = self._pending_macro_desc.get()
        i.comment = self._pending_comment.get() # Set comment if pending

        if self._pending_addr >= 0:
            i.abs_addr = self._pending_addr
            self._pending_addr = -1

        i.set_line_number(self._current_line_number)
        self._current_line_number = 0 # Reset for next instruction

        self._prog.append(i)

    def add_data_instruction(self, value: int):
         """Adds a data word directly into the program memory (Von Neumann)."""
         if not self._von_neumann:
              raise InstructionException(".data only allowed in Von Neumann mode (after .dorg)")

         label = self._pending_label.get() # Get pending label
         macro_desc = self._pending_macro_desc.get() # Consume pending

         data_instr = DataInstruction(value, self._current_line_number, label)

         if self._pending_addr >= 0:
              data_instr.abs_addr = self._pending_addr
              self._pending_addr = -1

         self._current_line_number = 0 # Reset for next instruction
         self._prog.append(data_instr)
         # Don't reset line number here

    def attach_same_line_comment_to_last(self, comment: str):
        """Attaches a comment found on the same line AFTER the last added item."""
        if not self._prog:
            # Comment appeared before anything was added, treat as pending for next
            self.add_pending_comment(comment)
            return

        last_item = self._prog[-1]
        # Ensure the last item can have a comment set
        if not hasattr(last_item, 'comment') or not callable(getattr(last_item, 'comment', None)):
             # Add a setter if missing, or handle error/warning
             # Assuming Instruction and DataInstruction have settable comments now.
             pass


        existing = last_item.comment
        new_comment = comment.strip() # Already stripped by tokenizer? Ensure it is.
        # Append same-line comment to any existing (likely preceding) comment.
        if existing:
            last_item.comment = existing + "\n" + new_comment # Use newline separator
        else:
            last_item.comment = new_comment


    def traverse(self, visitor: InstructionVisitor):
        """Traverses the program, calling the visitor for each instruction."""
        addr = 0
        self._addr_to_line_map.clear()
        last_addr = -1

        for i, instr in enumerate(self._prog):
            try:
                abs_addr = instr.abs_addr
                if abs_addr >= 0:
                    if abs_addr < addr:
                        # Allow setting current address, but not jumping back strictly
                        if abs_addr == last_addr and i>0 and self._prog[i-1].abs_addr == abs_addr:
                             # OK: Multiple instructions at same org address (e.g. label)
                             pass
                        else:
                            raise ExpressionException(
                                f".org cannot jump backward! Current addr={addr}, requested={abs_addr}",
                                instr.line_number)
                    # Fill potential gaps created by .org with NOPs or handle differently?
                    # For now, just jump the address counter. Hex formatter must handle gaps.
                    addr = abs_addr

                self._context.set_instr_addr(addr)
                # Calculate addresses for relative jumps/calls if needed by expressions
                next_addr = addr + self._calc_rel_addr(i, 1)
                skip_addr = addr + self._calc_rel_addr(i, 2)
                skip2_addr = addr + self._calc_rel_addr(i, 3)
                self._context.set_identifier(Context.NEXT_ADDR, next_addr)
                self._context.set_identifier(Context.SKIP_ADDR, skip_addr)
                self._context.set_identifier(Context.SKIP2_ADDR, skip2_addr)

                if not visitor.visit(instr, self._context):
                    break

                self._addr_to_line_map[addr] = instr.line_number
                last_addr = addr
                addr += instr.size

            except ExpressionException as e:
                e.set_line_number(instr.line_number) # Ensure line number is set
                raise e
            except Exception as e:
                 # Wrap unexpected errors
                 new_e = ExpressionException(f"Traversal error: {e}")
                 new_e.set_line_number(instr.line_number)
                 raise new_e from e

    def _calc_rel_addr(self, current_index: int, num_instructions_ahead: int) -> int:
        """Calculates the address offset for a number of instructions ahead."""
        offset = 0
        for j in range(num_instructions_ahead):
            idx = current_index + j
            if idx >= len(self._prog):
                break # Reached end of program
            offset += self._prog[idx].size
        return offset

    def _append_harvard_data(self):
        """Generates instructions to load Harvard data into RAM."""
        # Sort data map by value to potentially group loads? No, sort by address needed.
        # Need to insert these instructions *before* optimization and linking usually.
        # This approach is complex. Let's stick to Von Neumann for simplicity first.
        # If Harvard needed:
        #   data_instructions = []
        #   for value, addrs in sorted(self._data_map.items()):
        #      # Create LDI R?, value
        #      ldi = InstructionBuilder(Opcode.LDI).set_dest(Register.R0).set_constant_int(value).build()
        #      ldi.set_line_number(0) # Mark as generated
        #      data_instructions.append(ldi)
        #      for addr in sorted(addrs):
        #          # Create STS [addr], R?
        #          sts = InstructionBuilder(Opcode.STS).set_source(Register.R0).set_constant_int(addr).build()
        #          sts.set_line_number(0) # Mark as generated
        #          data_instructions.append(sts)
        #   # Insert these at the beginning or end? End is safer.
        #   self._prog.extend(data_instructions)
        if self._data_map:
             print("Warning: Harvard data (.word/.long/.data without .dorg) is not fully implemented for code generation in this Python version.")
        pass # Keep harvard logic minimal for now


    @property
    def instruction_count(self) -> int:
        return len(self._prog)

    def get_instruction(self, i: int) -> Optional[Instruction]:
        """Gets the i-th instruction if it's a standard Instruction."""
        instr = self._prog[i]
        return instr if isinstance(instr, Instruction) else None

    def add_ram(self, ident: str, size: int) -> int:
        if self._von_neumann:
            raise ExpressionException("Cannot use .word/.long/.words in Von Neumann mode after .dorg. Use .data instead.")

        # Consume label for this RAM definition
        label = self._pending_label.get()
        if label and label != ident:
             # Label before .word should match ident? Or just associate label with address?
             # Let's assume label before .word applies to the address definition.
             self._context.add_identifier(label, self._ram_pos)
             # Also add the ident itself
             if label.lower() != ident.lower():
                  self._context.add_identifier(ident, self._ram_pos)
        else:
            self._context.add_identifier(ident, self._ram_pos)

        # Consume other pending items that don't apply to RAM allocation
        self._pending_macro_desc.get()
        self._pending_comment.get()

        r = self._ram_pos
        self._ram_pos += size
        return r

    def add_data(self, value: int):
         """Adds constant data. Behavior depends on mode (Harvard vs Von Neumann)."""
         if self._von_neumann:
             # In Von Neumann, add as a DataInstruction at the current program address
             self.add_data_instruction(value)
         else:
             # In Harvard, store value and associate with the next RAM address
             label = self._pending_label.get() # Consume label if present
             if label:
                  self.add_ram(label, 0) # Add label pointing to current ram_pos

             current_ram_addr = self._ram_pos
             self._data_map[value].append(current_ram_addr)
             self._ram_pos += 1 # Allocate one word in RAM

    def add_data_label(self, ident: str):
        """Adds a label for the next data item."""
        if self._von_neumann:
            self.set_pending_label(ident)
        else:
            # For Harvard, label points to the RAM address
            self.add_ram(ident, 0)

    def set_pending_label(self, label: str):
        self._pending_label.set(label)

    def set_pending_macro_description(self, description: str):
        self._pending_macro_desc.set(description)

    def add_pending_comment(self, comment: str):
        # Allow multiple comments to accumulate
        current = self._pending_comment.get()
        if current:
            self._pending_comment.set(current + "\n" + comment.strip())
        else:
            self._pending_comment.set(comment.strip())


    def add_pending_origin(self, addr: int):
        if addr < 0:
             raise ValueError("Origin address cannot be negative")
        self._pending_addr = addr

    def set_ram_start(self, ram_start: int):
         """Sets the RAM start address and switches to Von Neumann mode."""
         if ram_start < 0:
              raise ValueError("RAM start address cannot be negative")
         if self._ram_pos != 0 or self._data_map: # Check if RAM/data already defined
             raise ExpressionException(".dorg must be used before any .word, .long, .data directives")
         self._ram_start_address = ram_start
         self._ram_pos = ram_start # Data starts here
         self._von_neumann = True
         # In Von Neumann, program counter and data pointer might need alignment?
         # Assume program counter starts at 0 unless .org is used.
         # Data will be placed according to program flow / .org / .dorg

    @property
    def context(self) -> Context:
        return self._context

    def get_line_by_addr(self, addr: int) -> int:
        """Gets the source line number for a given machine code address."""
        return self._addr_to_line_map.get(addr, -1)

    def optimize_and_link(self) -> 'Program':
        """Performs optimization and linking passes."""
        if not self._von_neumann:
            self._append_harvard_data() # Generate data loading code if needed

        # 1. First pass: Determine addresses and add labels to context
        self.traverse(LinkAddVisitor())

        # 2. Optimize short constants (replace LDI with LDIs etc.)
        self.traverse(OptimizerShort())

        # 3. Iteratively optimize jumps and update addresses
        while True:
            # Update labels based on potentially changed instruction sizes
            self.traverse(LinkSetVisitor())
            # Try to optimize long jumps to short jumps
            jmp_optimizer = OptimizerJmp()
            self.traverse(jmp_optimizer)
            if not jmp_optimizer.was_optimized:
                break # No more jump optimizations possible

        # 4. Final pass to set correct addresses for code generation
        self.traverse(LinkSetVisitor())
        return self

    def __str__(self) -> str:
        return "\n".join(str(i) for i in self._prog) + "\n"

    def write_addr_list(self, filename: str):
        """Writes a map file (address -> line number) in JSON format."""
        # Sort by address for readability
        sorted_map = sorted(self._addr_to_line_map.items())
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("[\n")
                first = True
                for addr, line in sorted_map:
                    if line > 0: # Only include lines with actual source mapping
                        if not first:
                            f.write(",\n")
                        f.write(f'  {{"addr":{addr},"line":{line}}}')
                        first = False
                f.write("\n]\n")
        except IOError as e:
             print(f"Error writing address list file {filename}: {e}")


# --- Visitor Implementations (nested or separate classes) ---
class LinkAddVisitor(InstructionVisitor):
    """Visitor to add labels to the context during the first pass."""
    def visit(self, instruction: InstructionInterface, context: Context) -> bool:
        if instruction.label:
            context.add_identifier(instruction.label, context.instr_addr)
        return True

class LinkSetVisitor(InstructionVisitor):
    """Visitor to update label addresses in the context."""
    def visit(self, instruction: InstructionInterface, context: Context) -> bool:
        if instruction.label:
            # Use set_identifier to allow updates after optimization changed sizes
            context.set_identifier(instruction.label, context.instr_addr)
        return True


