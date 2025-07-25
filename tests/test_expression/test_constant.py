import pytest
from assembler.expression import Constant, ExpressionException

def test_get_value():
    assert Constant('A').get_value(None) == 0x41
    assert Constant(ord('A')).get_value(None) == 0x41
    assert Constant(65).get_value(None) == 65

def test_to_string():
    assert str(Constant('A')) == "'A'"
    assert str(Constant(65)) == "65"
    assert str(Constant('\n')) == "'\\n'"
    assert str(Constant('\r')) == "'\\r'"
    assert str(Constant('\t')) == "'\\t'"
    assert str(Constant('\b')) == "'\\b'"
    assert str(Constant('"')) == "'\\\"'" # String needs escaping for Python syntax too
    assert str(Constant('\\')) == "'\\\\'"
    assert str(Constant('\'')) == "'\\''"
    assert str(Constant('\0')) == "'\\0'"
    # Non-printable example
    assert str(Constant('\x01')) == "'\\x01'"

def test_invalid_char():
     with pytest.raises(ValueError):
          Constant("AA")
     with pytest.raises(ValueError):
          Constant("")
