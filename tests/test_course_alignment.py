import pytest
from lark.exceptions import UnexpectedInput
from sipl.ast import LogicalNot, LogicalOr, Block, If
from sipl.course import parse_course, parse_course_ast, run_course
from sipl.interpreter import SIPLRuntimeError, StepLimitExceeded


@pytest.mark.parametrize("program,state", [
    ("begin skip end", {}),
    ("begin X := -3 end", {"X": -3}),
    ("begin X := 1; Y := X + 2 * 3 end", {"X": 1, "Y": 7}),
    ("begin X := 5; if X > 3 then Y := 1 else Y := 0 end", {"X": 5, "Y": 1}),
    ("begin X := 5; if X = 3 then Y := 1 else Y := 0 end", {"X": 5, "Y": 0}),
    ("begin X := 5; if ¬(X = 0) then Y := 1 else Y := 0 end", {"X": 5, "Y": 1}),
    ("begin X := 0; if (X = 0) ∨ (Y > 0) then Z := 1 else Z := 0 end", {"X": 0, "Z": 1}),
    ("begin X := 0; if ¬(X = 0 ∨ X > 2) then Z := 1 else Z := 0 end", {"X": 0, "Z": 0}),
    ("begin X := 3; while X > 0 do X := X - 1 end", {"X": 0}),
    ("begin X := 1; begin X := X + 1; X := X * 2 end end", {"X": 4}),
    ("begin X := -(2 + 3) end", {"X": -5}),
])
def test_valid_course_programs(program, state):
    assert run_course(program) == state


@pytest.mark.parametrize("program", [
    "skip", "X := 1", "begin end", "begin X := 1; end", "begin X := 1 / 2 end",
    "begin if X < 3 then skip else skip end", "begin if X != 3 then skip else skip end",
    "begin if X >= 3 then skip else skip end", "begin X := 1; end",
    "begin while X > 0 X := X - 1 end", "begin x := 1 end",
])
def test_invalid_course_programs(program):
    with pytest.raises(UnexpectedInput):
        parse_course(program)


def test_typed_conditions():
    node = parse_course_ast("begin if ¬(X = 0) ∨ (Y > 0) then skip else skip end")
    assert isinstance(node, Block)
    assert isinstance(node.statements[0], If)
    assert isinstance(node.statements[0].condition, LogicalOr)
    assert isinstance(node.statements[0].condition.left, LogicalNot)


def test_short_circuit():
    assert run_course("begin X := 0; if X = 0 ∨ Y > 0 then X := 1 else skip end") == {"X": 1}


def test_runtime_errors():
    with pytest.raises(SIPLRuntimeError, match="Undefined variable"):
        run_course("begin X := Y end")
    with pytest.raises(StepLimitExceeded):
        run_course("begin X := 1; while X > 0 do skip end", max_steps=10)
