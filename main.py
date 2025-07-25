import sys
import argparse
import traceback
from assembler.parser import Parser
from assembler.asm import Program
from assembler.asm.formatters import HexFormatter, AsmFormatter
from assembler.expression import ExpressionException
from assembler.parser import ParserException
from assembler.asm import InstructionException

def assemble_file(input_filename: str, output_hex: str = None, output_lst: str = None, output_map: str = None):
    """Assembles a file and produces specified output files."""
    print(f"Assembling {input_filename}...")
    program = None
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            parser = Parser(f, base_file=input_filename)
            program = parser.parse_program()
            print("Parsing complete. Optimizing and linking...")
            program.optimize_and_link()
            print("Linking complete.")

        if output_hex:
            print(f"Writing hex file to {output_hex}...")
            with open(output_hex, 'w', encoding='utf-8') as f:
                formatter = HexFormatter(f)
                program.traverse(formatter)
                formatter.finalize() # Important for HexFormatter

        if output_lst:
            print(f"Writing listing file to {output_lst}...")
            with open(output_lst, 'w', encoding='utf-8') as f:
                formatter = AsmFormatter(f)
                program.traverse(formatter)

        if output_map:
             print(f"Writing map file to {output_map}...")
             program.write_addr_list(output_map)

        print("Assembly successful.")

    except (ParserException, InstructionException, ExpressionException) as e:
        print(f"\nAssembly failed: {e}", file=sys.stderr)
        # traceback.print_exc()
        sys.exit(1)
    except FileNotFoundError:
        print(f"\nError: Input file not found: {input_filename}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Assemble a file for the custom 16-bit processor.")
    arg_parser.add_argument("input_file", help="Path to the input .asm file.")
    arg_parser.add_argument("-o", "--output", help="Base name for output files (.hex, .lst, .map will be appended). "
                                                 "Defaults to input file base name.")
    arg_parser.add_argument("--hex", action="store_true", help="Generate .hex file (default if no specific output selected).")
    arg_parser.add_argument("--lst", action="store_true", help="Generate .lst file.")
    arg_parser.add_argument("--map", action="store_true", help="Generate .map file.")
    arg_parser.add_argument("--all", action="store_true", help="Generate all output files (.hex, .lst, .map).")

    args = arg_parser.parse_args()

    input_base = args.input_file.rsplit('.', 1)[0]
    output_base = args.output if args.output else input_base

    gen_hex = args.hex or args.all
    gen_lst = args.lst or args.all
    gen_map = args.map or args.all

    # Default to generating hex if no specific output is chosen
    if not (gen_hex or gen_lst or gen_map):
        gen_hex = True

    hex_file = f"{output_base}.hex" if gen_hex else None
    lst_file = f"{output_base}.lst" if gen_lst else None
    map_file = f"{output_base}.map" if gen_map else None

    assemble_file(args.input_file, hex_file, lst_file, map_file)
