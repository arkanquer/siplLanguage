"""CORE-03 tests: arithmetic, sequencing, branching, loops, errors and budget."""
import pytest

from sipl.interpreter import Interpreter, SIPLRuntimeError, StepLimitExceeded, run
from sipl.parser import parse_ast


@pytest.mark.parametrize("source, expected", [
    ("X := 7", {"X": 7}),
    ("X := 2 + 3 * 4", {"X": 14}),
    ("X := (2 + 3) * 4", {"X": 20}),
    ("X := 9 / 2", {"X": 4}),
    ("X := 3 - 8", {"X": -5}),
    ("begin X := 1; Y := X + 4 end", {"X": 1, "Y": 5}),
    ("begin X := 1; skip; X := X + 1 end", {"X": 2}),
    ("if 2 > 1 then X := 10 else X := 20", {"X": 10}),
    ("if 2 < 1 then X := 10 else X := 20", {"X": 20}),
    ("begin X := 3; while X > 0 do X := X - 1 end", {"X": 0}),
    ("begin X := 5; Y := 3; R := 0; while Y > 0 do begin R := R + X; Y := Y - 1 end end",
     {"X": 5, "Y": 0, "R": 15}),
    ("begin X := 3; while X < 0 do X := X - 1 end", {"X": 3}),
    ("begin X := 2; Y := 2; while X > 0 do begin Y := Y * 2; X := X - 1 end end",
     {"X": 0, "Y": 8}),
    ("X := 0 / 4", {"X": 0}),
    ("begin X := 0 - 9; Y := X / 2 end", {"X": -9, "Y": -4}),
])
def test_valid_execution(source, expected):
    assert run(source) == expected


@pytest.mark.parametrize("op, left, right, expected", [
    ("=", 2, 2, True), ("=", 2, 3, False),
    ("!=", 2, 3, True), ("!=", 2, 2, False),
    ("<", 2, 3, True), ("<", 3, 2, False),
    ("<=", 3, 3, True), ("<=", 4, 3, False),
    (">", 3, 2, True), (">", 2, 3, False),
    (">=", 3, 3, True), (">=", 2, 3, False),
])
def test_comparisons(op, left, right, expected):
    program = f"if {left} {op} {right} then X := 1 else X := 0"
    assert run(program)["X"] == int(expected)


def test_initial_state_is_copied():
    initial = {"X": 2}
    runtime = Interpreter(initial)
    assert runtime.execute(parse_ast("X := X + 3")) == {"X": 5}
    assert initial == {"X": 2}


def test_result_is_copy():
    runtime = Interpreter()
    result = runtime.execute(parse_ast("X := 5"))
    result["X"] = 99
    assert runtime.state["X"] == 5


def test_unknown_variable_has_location():
    with pytest.raises(SIPLRuntimeError, match=r"line 1, column 6: Undefined variable 'Y'"):
        run("X := Y + 1")


def test_division_by_zero_has_location():
    with pytest.raises(SIPLRuntimeError, match="Division by zero"):
        run("X := 4 / 0")


def test_infinite_loop_is_stopped():
    with pytest.raises(StepLimitExceeded, match="Execution step limit exceeded"):
        run("while 1 = 1 do skip", max_steps=25)


def test_finite_program_also_obeys_step_limit():
    with pytest.raises(StepLimitExceeded):
        run("begin X := 1; Y := 2 end", max_steps=2)


def test_step_count_is_deterministic():
    runtime = Interpreter(max_steps=10)
    assert runtime.execute(parse_ast("while 1 = 0 do skip")) == {}
    assert runtime.steps == 2  # while statement + false condition


@pytest.mark.parametrize("bad", [0, -1])
def test_rejects_invalid_step_limit(bad):
    with pytest.raises(ValueError):
        Interpreter(max_steps=bad)


def test_rejects_noninteger_state():
    with pytest.raises(ValueError):
        Interpreter({"X": "abc"})


def test_cli_run_success(tmp_path):
    import subprocess
    import sys
    path = tmp_path / "example.sipl"
    path.write_text("begin X := 5; Y := X + 1 end", encoding="utf-8")
    process = subprocess.run([sys.executable, "-m", "sipl.cli", str(path), "--run"],
                             capture_output=True, text=True)
    assert process.returncode == 0
    assert "X = 5" in process.stdout and "Y = 6" in process.stdout


def test_cli_run_failure(tmp_path):
    import subprocess
    import sys
    path = tmp_path / "example.sipl"
    path.write_text("X := Y", encoding="utf-8")
    process = subprocess.run([sys.executable, "-m", "sipl.cli", str(path), "--run"],
                             capture_output=True, text=True)
    assert process.returncode != 0
    assert "Undefined variable" in process.stdout
