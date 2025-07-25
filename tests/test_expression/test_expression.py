import pytest
from assembler.expression import Context, ExpressionException, Constant, Identifier, Expression
from assembler.parser import Parser, ParserException  # Use parser to create expressions

def parse_expr(code: str) -> Expression:
     # Helper to parse an expression string
     return Parser(code).parse_expression()

def test_simple():
    assert parse_expr("1+2").get_value(None) == 3

def test_simple_neg():
    assert parse_expr("-1").get_value(None) == -1
    assert parse_expr("- (1+2)").get_value(None) == -3

def test_simple_inv():
    assert parse_expr("~1").get_value(None) == -2  # ~1 is -2 in two's complement
    assert parse_expr("~0").get_value(None) == -1

def test_simple_hex():
    assert parse_expr("0xff").get_value(None) == 255

def test_simple_bin():
    assert parse_expr("0b101").get_value(None) == 5

def test_simple_sub():
    assert parse_expr("2-1").get_value(None) == 1

def test_precedence():
    assert parse_expr("2*2+3").get_value(None) == 7
    assert parse_expr("2*(2+3)").get_value(None) == 10
    assert parse_expr("(2+4)/2").get_value(None) == 3 # Integer division

def test_logical():
    # Note: Python 'and', 'or' are short-circuiting logical operators.
    # The parser uses bitwise operators based on Java code (&, |, ^).
    # Need to use bitwise operators or keywords if defined that way.
    # Assuming parser implements AND, OR, XOR keywords as bitwise:
    assert parse_expr("2 and (2 or 8) and 8").get_value(None) == 0 # 2 & (2|8) & 8 = 2 & 10 & 8 = 2 & 8 = 0
    # Java parser had 'AND', 'OR' as keywords. Python parser needs adjustment if using '&' etc.
    # Let's assume the parser maps 'and'/'or'/'xor' to bitwise ops:
    assert parse_expr("2 and 2 or 8 and 8").get_value(None) == 10 # (2&2)|(8&8) = 2 | 8 = 10 (assuming standard precedence)
    assert parse_expr("(2 and 2) or (8 and 8)").get_value(None) == 10 # 2 | 8 = 10

def test_identifier():
    context = Context().add_identifier("A", 3)
    assert parse_expr("2*(A+4)").get_value(context) == 14

def test_char_literal():
    assert parse_expr("5+'A'").get_value(None) == 5 + ord('A')
    with pytest.raises(ParserException): # Our tokenizer should raise this
         parse_expr("5+'AA'")

def test_to_string():
    assert str(parse_expr("5+'A'")) == "5+'A'"
    assert str(parse_expr("2*(1+3)")) == "2*(1+3)"
    assert str(parse_expr("0xff")) == "255" # Constant converts back to decimal str
    assert str(parse_expr("~1")) == "~1"
    assert str(parse_expr("-(1+2)")) == "-(1+2)"

