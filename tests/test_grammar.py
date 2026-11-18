import pytest
from lark.exceptions import LarkError
from sipl.parser import parse

VALID = [
    "skip",
    "X := 1",
    "X := 123",
    "X := Y",
    "X := 1 + 2 * 3",
    "X := (1 + 2) * 3",
    "begin skip end",
    "begin X := 1; Y := 2 end",
    "if X > 0 then Y := 1 else Y := 0",
    "while X > 0 do X := X - 1",
    "begin X := 3; while X > 0 do begin X := X - 1; skip end end",
    "if (X <= 10) then skip else X := 10",
]

INVALID = [
    "",
    "X = 1",
    "X :=",
    "begin",
    "begin X := 1",
    "while X > 0 X := 1",
    "if X > 0 Y := 1 else Y := 0",
    "if X > 0 then Y := 1",
    "X := (1 + 2",
    "X := 1 + * 2",
    "begin ; skip end",
    "X := @",
]

@pytest.mark.parametrize("source", VALID)
def test_accepts_valid_programs(source):
    assert parse(source) is not None

@pytest.mark.parametrize("source", INVALID)
def test_rejects_invalid_programs(source):
    with pytest.raises(LarkError):
        parse(source)
