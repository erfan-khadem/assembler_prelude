import io
import os
import re

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TextIO, Optional, Dict, Tuple, List, Type, Union
from enum import Enum, auto

from assembler.asm import (
    Program, Opcode, Register, InstructionBuilder, Instruction, InstructionException,
    MnemonicArguments, MNEMONIC_ARG_LOOKUP
)
from assembler.expression import (
    Expression, Context, ExpressionException, Constant, Identifier, Neg, NotOp, Operate, Operation
)
from .parser_exception import ParserException
from .macro import Macro
from .macros import ALL_MACROS # Import the list of macro classes


class TokenType(Enum):
    COMMENT = auto()
    LABELDEF = auto()
    STRING = auto()
    CHAR = auto()
    HEX = auto()
    BIN = auto()
    DEC = auto()
    DOTCMD = auto()
    WORD = auto()
    OP = auto()
    NEWLINE = auto()
    SKIP = auto()
    MISMATCH = auto()
    EOF = auto()

    @classmethod
    def from_str(cls, type: str) -> 'TokenType':
        return cls[type]


# --- Tokenizer ---
# Simple regex-based tokenizer for this assembly language
TOKEN_SPEC = [
    (TokenType.COMMENT, r';[^\r\n]*|/\*.*?\*/'), # Line comments or block comments
    (TokenType.LABELDEF,r'([a-zA-Z_][a-zA-Z0-9_]*):'),# Label definition (ends with :)
    (TokenType.STRING,  r'"([^"\\]*(?:\\.[^"\\]*)*)"'), # Double-quoted strings
    (TokenType.CHAR,    r"'([^'\\]*(?:\\.[^'\\]*)*)'"), # Single-quoted char
    (TokenType.HEX,     r'0x[0-9a-fA-F]+'),           # Hexadecimal number
    (TokenType.BIN,     r'0b[01]+'),                  # Binary number
    (TokenType.DEC,     r'[0-9]+'),                   # Decimal number
    (TokenType.DOTCMD,  r'\.[a-zA-Z_]+'),             # Directive like .data, .org
    (TokenType.WORD,    r'[a-zA-Z_][a-zA-Z0-9_]*'),   # Identifiers, opcodes, registers
    (TokenType.OP,      r'[+\-*/&|^~()\[\],]'),       # Operators and punctuation
    (TokenType.NEWLINE, r'[\r\n]+'),                  # Newline
    (TokenType.SKIP,    r'[ \t]+'),                   # Skip whitespace
    (TokenType.MISMATCH,r'.'),                        # Any other character
]
TOK_REGEX = '|'.join(f'(?P<{pair[0].name}>{pair[1]})' for pair in TOKEN_SPEC)

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int


def tokenize(code: str) -> List[Token]:
    line_num = 1
    line_start = 0
    tokens = []
    for mo in re.finditer(TOK_REGEX, code, re.DOTALL | re.MULTILINE):
        kind = TokenType.from_str(mo.lastgroup)
        value = mo.group()
        column = mo.start() - line_start
        if kind == TokenType.NEWLINE:
            line_start = mo.end()
            line_num += value.count('\n')
        elif kind == TokenType.SKIP: # Only skip whitespace
            pass
        elif kind == TokenType.MISMATCH:
            raise ParserException(f'Unexpected character: {value!r}', line_num)
        else:
            # Handle specific token types (LABELDEF, STRING, CHAR) as before...
            if kind == TokenType.LABELDEF: value = value[:-1]
            elif kind == TokenType.STRING: value = value[1:-1].encode().decode('unicode_escape')
            elif kind == TokenType.CHAR:
                value = value[1:-1].encode().decode('unicode_escape')
                if len(value) != 1: raise ParserException(f"Invalid character literal: '{value}'", line_num)

            tokens.append(Token(kind, value, line_num, column))
    tokens.append(Token(TokenType.EOF, '', line_num, 0))
    return tokens


# --- Parser Directives ---
class Directive(ABC):
    def __init__(self, name: str, args_desc: str, description: str):
        self.name = name
        self.args_desc = args_desc
        self.description = description
    @abstractmethod
    def do_work(self, parser: 'Parser', program: Program): pass
    def __str__(self) -> str: return f"{self.name} {self.args_desc}\n\t{self.description}"

class DReg(Directive):
    def __init__(self): super().__init__(".reg", "alias Rs", "Sets an alias name for a register.")
    def do_work(self, parser: 'Parser', program: Program):
        alias = parser.parse_word()
        program.add_pending_comment(f" {alias}")
        reg = parser.parse_reg()
        program.add_pending_comment(f" {reg.name}")
        parser.regs_map[alias] = reg
class DWord(Directive):
    def __init__(self): super().__init__(".word", "addr", "Reserves a single word in the RAM. Its address is stored in addr.")
    def do_work(self, parser: 'Parser', program: Program):
        ident = parser.parse_word()
        program.add_pending_comment(f" {ident}")
        program.add_ram(ident, 1)
class DLong(Directive):
    def __init__(self): super().__init__(".long", "addr", "Reserves two words in the RAM. Its address is stored in addr.")
    def do_work(self, parser: 'Parser', program: Program):
        ident = parser.parse_word()
        program.add_pending_comment(f" {ident}")
        program.add_ram(ident, 2)
class DWords(Directive): # Added based on Java comments/test
    def __init__(self): super().__init__(".words", "addr size", "Reserves [size] words in the RAM. Its address is stored in addr.")
    def do_work(self, parser: 'Parser', program: Program):
        ident = parser.parse_word()
        size_expr = parser.parse_expression()
        try:
            size = size_expr.get_value(program.context)
            if size < 0: raise ParserException("Size for .words must be non-negative", parser.current_token.line)
        except ExpressionException as e:
            raise ParserException(f"Could not evaluate size for .words: {e}", parser.current_token.line) from e
        program.add_pending_comment(f" {ident} {size}")
        program.add_ram(ident, size)
class DOrg(Directive):
    def __init__(self): super().__init__(".org", "addr", "Sets the actual code address. Is used to place code segments to fixed addresses.")
    def do_work(self, parser: 'Parser', program: Program):
        addr_expr = parser.parse_expression()
        try:
             # Evaluate immediately if possible, otherwise linking handles it?
             # The Java version seems to evaluate later. Let's store the expression.
             # Hmm, Java's Program.addPendingOrigin takes int. Let's evaluate now.
             addr = addr_expr.get_value(program.context)
             program.add_pending_origin(addr)
             program.add_pending_comment(f" 0x{addr:x}")
        except ExpressionException as e:
             # For now, require constants resolvable at parse time for .org
             raise ParserException(f"Could not evaluate address for .org: {e}", parser.current_token.line) from e
class DDOrg(Directive):
    def __init__(self): super().__init__(".dorg", "addr", "Sets the actual data address. If used, assembler is switched to von Neumann mode.")
    def do_work(self, parser: 'Parser', program: Program):
        addr_expr = parser.parse_expression()
        try:
             addr = addr_expr.get_value(program.context)
             program.set_ram_start(addr)
             program.add_pending_comment(f" 0x{addr:x}")
        except ExpressionException as e:
             raise ParserException(f"Could not evaluate address for .dorg: {e}", parser.current_token.line) from e
class DData(Directive):
    def __init__(self): super().__init__(".data", "addr value(,value)*", "Copies the given values to the RAM/program memory. The address of the values is stored in addr.")
    def do_work(self, parser: 'Parser', program: Program):
        ident = parser.parse_word()
        program.add_pending_comment(f" {ident}")
        program.add_data_label(ident) # CORRECTED method name
        parser._read_data_value(program)
        while parser.check_and_consume(','):
            program.add_pending_comment(", ")
            parser._read_data_value(program)

class DConst(Directive):
    def __init__(self): super().__init__(".const", "ident const", "Creates the given constant.")
    def do_work(self, parser: 'Parser', program: Program):
        ident = parser.parse_word()
        value_expr = parser.parse_expression()
        try:
            value = value_expr.get_value(program.context)
            program.add_pending_comment(f" {ident} {value}")
            program.context.add_identifier(ident, value)
        except ExpressionException as e:
             # Allow forward references? No, Java seems to evaluate immediately.
             raise ParserException(f"Could not evaluate value for .const '{ident}': {e}", parser.current_token.line) from e

class DInclude(Directive):
     def __init__(self): super().__init__(".include", "\"filename\"", "Includes the given file.")
     def do_work(self, parser: 'Parser', program: Program):
         if parser.current_token.type != TokenType.STRING:
              raise parser.make_parser_exception("Expected string filename for .include")
         filename = parser.current_token.value
         parser.advance() # Consume filename

         if parser.base_file is None:
              raise parser.make_parser_exception(".include needs a base file context")

         include_path = os.path.join(os.path.dirname(parser.base_file), filename)
         program.add_pending_comment(f"\n; <<< Included: {filename} >>>\n")
         try:
             with open(include_path, 'r', encoding='utf-8') as f:
                  # Create a new parser instance for the included file
                  inc_parser = Parser(f, base_file=include_path, existing_program=program)
                  # Parse into the *existing* program object
                  inc_parser.parse_program()
         except FileNotFoundError:
              raise parser.make_parser_exception(f"Include file not found: {include_path}")
         except Exception as e:
              raise parser.make_parser_exception(f"Error parsing include file {filename}: {e}") from e
         program.add_pending_comment(f"\n; <<< End Include: {filename} >>>\n")


# --- Parser Class ---
class Parser:
    # Class-level dictionaries for macros and directives
    MACROS: Dict[str, Macro] = {m.name.lower(): m for m in ALL_MACROS}
    DIRECTIVES: Dict[str, Directive] = {
        d.name.lower(): d for d in [
            DReg(), DWord(), DLong(), DWords(), DOrg(), DDOrg(), DData(), DConst(), DInclude()
        ]
    }

    def __init__(self, source: Union[TextIO, str], base_file: Optional[str] = None, existing_program: Optional[Program] = None):
        if isinstance(source, str):
            self.reader = io.StringIO(source)
            self.code = source
        else:
            self.reader = source
            self.code = self.reader.read() # Read whole content for regex tokenizer
            self.reader.seek(0) # Reset reader if needed elsewhere (not needed for tokenize)

        self.base_file = base_file
        self.tokens: List[Token] = tokenize(self.code)
        self.token_index: int = 0
        self.current_token: Token = self.tokens[0] if self.tokens else Token(TokenType.EOF,'',0,0)
        self.regs_map: Dict[str, Register] = {} # For .reg directive

        # Use existing program or create a new one
        self.program = existing_program if existing_program is not None else Program()

    @staticmethod
    def get_macros() -> List[Macro]:
         return list(Parser.MACROS.values())
    @staticmethod
    def get_directives() -> List[Directive]:
         return list(Parser.DIRECTIVES.values())

    def advance(self):
        """Move to the next token."""
        self.token_index += 1
        if self.token_index < len(self.tokens):
            self.current_token = self.tokens[self.token_index]
        else:
             # Should already be EOF, but handle gracefully if called again
             self.current_token = self.tokens[-1] # Stay at EOF

    def make_parser_exception(self, message: str) -> ParserException:
        """Create a ParserException with the current line number."""
        line = self.current_token.line if self.current_token else 0
        return ParserException(message, line)

    def consume(self, expected: str):
        """Consume the current token if it matches expected, otherwise raise error."""
        # Expected can be a token type (e.g., 'WORD') or a specific value (e.g., '[')
        if self.current_token.type == TokenType.EOF:
             raise self.make_parser_exception(f"Expected '{expected}' but found end of file")

        # Check type or value based on expected format
        is_type_match = type(expected) is TokenType
        match_target = self.current_token.type if is_type_match else self.current_token.value

        if match_target == expected:
            self.advance()
        else:
            display_expected = f"token type {expected}" if is_type_match else f"'{expected}'"
            found_val = f"'{self.current_token.value}'" if self.current_token.value else ""
            raise self.make_parser_exception(f"Expected {display_expected}, but found {self.current_token.type} {found_val}")

    def check_and_consume(self, value: str) -> bool:
         """Check if the current token value matches, consume if it does."""
         if self.current_token.type != TokenType.EOF and self.current_token.value == value:
              self.advance()
              return True
         return False

    def is_next(self, value: str) -> bool:
        """Check if the current token value matches without consuming."""
        return self.current_token.type != TokenType.EOF and self.current_token.value == value

    def is_eol(self) -> bool:
         """Check if the current token indicates end of line or file."""
         # Our tokenizer skips NEWLINE, so check for EOF or next significant token's line
         if self.current_token.type == TokenType.EOF:
              return True
         # Look ahead slightly - if next token is on a new line, consider current EOL
         if self.token_index + 1 < len(self.tokens):
              next_token = self.tokens[self.token_index] # Current token is the one we check
              peek_token = self.tokens[self.token_index + 1]
              # Is the *next* token on a different line?
              # No, check current token. Tokenizer gives us significant tokens only.
              # If the *previous* token was on a different line, maybe?
              # Simplest: Assume EOL logic is handled by main parsing loop structure.
              # The Java version used eolIsSignificant. Our tokenizer doesn't.
              # We rely on the parsing loop structure. This function might not be needed
              # or needs to be implemented based on line numbers if essential.
              # Let's assume it checks if the *current* token is EOF for now.
              return False # Only EOF is true EOL in this tokenizer setup
         return False # Should not happen if EOF is last


    def _check_and_attach_comment(self, processed_line: int):
        """Checks if the current token is a comment on the same line
           as the item just processed and attaches it to the last added program item."""
        # Loop to consume all comments on the same line
        attached_comment = False
        while self.current_token.type == TokenType.COMMENT and self.current_token.line == processed_line:
            comment_value = self.current_token.value
            self.program.attach_same_line_comment_to_last(comment_value)
            self.advance() # Consume the comment token
            attached_comment = True
        return attached_comment

    def parse_program(self) -> Program:
        """Parses the entire program from the token stream."""
        while self.current_token.type != TokenType.EOF:
            token = self.current_token
            self.program.set_line_number(token.line)

            if token.type == TokenType.LABELDEF:
                self.program.set_pending_label(token.value)
                self.advance() # Consume label definition
                label_line = token.line
                self._check_and_attach_comment(label_line)
                # Label might be on its own line, continue loop
                continue

            elif token.type == TokenType.DOTCMD:
                 cmd = token.value.lower()
                 directive = Parser.DIRECTIVES.get(cmd)
                 if not directive:
                      raise self.make_parser_exception(f"Unknown directive: {token.value}")
                 self.program.add_pending_comment(f"\n {token.value}") # Log directive use
                 self.advance() # Consume directive token
                 directive.do_work(self, self.program)
                 directive_line = token.line
                 self._check_and_attach_comment(directive_line)
                 # Directives usually consume the rest of their line implicitly

            elif token.type == TokenType.COMMENT:
                # Attach comment to the program's pending state
                self.program.add_pending_comment(token.value)
                self.advance()
                continue # Comments can be on their own line

            elif token.type == TokenType.WORD:
                word = token.value
                word_lower = word.lower()
                opcode = Opcode.parse_str(word)
                macro = Parser.MACROS.get(word_lower)
                instruction_line = token.line


                if opcode:
                    self.advance() # Consume opcode
                    self._parse_instruction(opcode)
                    self._check_and_attach_comment(instruction_line)
                elif macro:
                    self.advance() # Consume macro name
                    macro.parse_macro(self.program, macro.name, self)
                    self._check_and_attach_comment(instruction_line)
                else:
                    # Should have been caught as LABELDEF if followed by ':'
                    # Otherwise, it's an error here.
                     raise self.make_parser_exception(f"Unexpected identifier: {word}. Expected opcode, macro, or directive.")

            elif token.type == TokenType.EOF:
                 break # Should be caught by loop condition, but safe check
            else:
                 # Might be punctuation left from previous parse, or unexpected token
                 raise self.make_parser_exception(f"Unexpected token: {token.type} '{token.value}'")

            # After processing a line (instruction, directive, macro), expect EOF or implicitly handled newline
            if self.current_token.type != TokenType.EOF:
                 # Our tokenizer skips explicit newlines. If not EOF, it should be start of next item.
                 pass

        return self.program


    def _parse_instruction(self, opcode: Opcode):
        """Parses a standard instruction after the opcode has been consumed."""
        builder = InstructionBuilder(opcode)
        # Let the MnemonicArguments handle parsing based on opcode's expected args
        try:
            opcode.arguments.parse(builder, self)
            instruction = builder.build()
            self.program.add(instruction)
        except (InstructionException, ParserException, ExpressionException) as e:
            # Add line number context if possible
            if isinstance(e, (ParserException, ExpressionException)) and e.line_number <= 0:
                 e.set_line_number(self.current_token.line)
            raise e # Re-raise exceptions

    def _read_data_value(self, program: Program):
         """Helper to parse a single value for .data directive."""
         if self.current_token.type == TokenType.STRING:
              text = self.current_token.value
              program.add_pending_comment(f" \"{self._escape_text(text)}\"")
              for char in text:
                   program.add_data(ord(char))
              self.advance()
         else:
              # Assume integer expression
              expr = self.parse_expression()
              try:
                   value = expr.get_value(program.context)
                   program.add_pending_comment(f" {value}")
                   program.add_data(value)
              except ExpressionException as e:
                   raise self.make_parser_exception(f"Could not evaluate .data value: {e}") from e

    def _escape_text(self, text: str) -> str:
         """Escape text for comments, similar to Java version."""
         escaped = ""
         for char in text:
             val = ord(char)
             if 32 <= val < 127:
                  if char == '"': escaped += '\\"'
                  elif char == '\\': escaped += '\\\\'
                  else: escaped += char
             else:
                  escape_map = {'\n': '\\n', '\r': '\\r', '\t': '\\t'}
                  escaped += escape_map.get(char, f"\\x{val:02x}")
         return escaped

    # --- Expression Parsing (Recursive Descent) ---
    # Based on standard operator precedence: PAREN > NOT/NEG > MUL/DIV > ADD/SUB > AND > XOR > OR

    def parse_expression(self) -> Expression:
        return self._parse_or()

    def _parse_or(self) -> Expression:
        expr = self._parse_xor()
        while self.check_and_consume('or'): # Assumes 'or' is tokenized as WORD 'or'
            expr = Operate(expr, Operation.OR, self._parse_xor())
        return expr

    def _parse_xor(self) -> Expression:
        expr = self._parse_and()
        while self.check_and_consume('xor'): # Assumes 'xor' is tokenized as WORD 'xor'
            expr = Operate(expr, Operation.XOR, self._parse_and())
        return expr

    def _parse_and(self) -> Expression:
        expr = self._parse_add_sub()
        while self.check_and_consume('and'): # Assumes 'and' is tokenized as WORD 'and'
             expr = Operate(expr, Operation.AND, self._parse_add_sub())
        return expr

    def _parse_add_sub(self) -> Expression:
        expr = self._parse_mul_div()
        while self.current_token.value in ['+', '-']:
            op_val = self.current_token.value
            self.advance()
            op = Operation.ADD if op_val == '+' else Operation.SUB
            expr = Operate(expr, op, self._parse_mul_div())
        return expr

    def _parse_mul_div(self) -> Expression:
        expr = self._parse_unary()
        while self.current_token.value in ['*', '/']:
            op_val = self.current_token.value
            self.advance()
            op = Operation.MUL if op_val == '*' else Operation.DIV
            expr = Operate(expr, op, self._parse_unary())
        return expr

    def _parse_unary(self) -> Expression:
        if self.check_and_consume('-'):
            return Neg(self._parse_unary()) # Recursively parse unary for -- or -~
        if self.check_and_consume('~'):
            return NotOp(self._parse_unary()) # Recursively parse unary
        return self._parse_primary()

    def _parse_primary(self) -> Expression:
        token = self.current_token
        if token.type == TokenType.DEC:
             val = int(token.value)
             self.advance()
             return Constant(val)
        elif token.type == TokenType.HEX:
             val = int(token.value, 16)
             self.advance()
             return Constant(val)
        elif token.type == TokenType.BIN:
             val = int(token.value, 2)
             self.advance()
             return Constant(val)
        elif token.type == TokenType.CHAR:
             val = token.value # Already decoded char
             self.advance()
             return Constant(val)
        elif token.type == TokenType.WORD:
             # Could be register or identifier
             # Registers shouldn't appear in general expression. Assume identifier.
             name = token.value
             self.advance()
             return Identifier(name)
        elif self.check_and_consume('('):
            expr = self.parse_expression()
            self.consume(')')
            return expr
        else:
            raise self.make_parser_exception(f"Unexpected token in expression: {token.type} '{token.value}'")

    # --- Other Parsing Helpers ---
    def parse_reg(self) -> Register:
        """Parses a register name."""
        if self.current_token.type != TokenType.WORD:
            raise self.make_parser_exception(f"Expected register name, found {self.current_token.type}")
        name = self.current_token.value
        reg = Register.parse_str(name)
        if reg is not None:
            self.advance()
            return reg

        # Check for alias defined by .reg
        aliased_reg = self.regs_map.get(name)
        if aliased_reg is not None:
            self.advance()
            return aliased_reg

        raise self.make_parser_exception(f"Expected a register name, found '{name}'")

    def parse_word(self) -> str:
        """Parses a WORD token."""
        if self.current_token.type != TokenType.WORD:
             raise self.make_parser_exception(f"Expected identifier/word, found {self.current_token.type} '{self.current_token.value}'")
        val = self.current_token.value
        self.advance()
        return val
