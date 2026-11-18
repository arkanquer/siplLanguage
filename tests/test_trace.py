import json
import subprocess
import sys

import pytest

from sipl.interpreter import Interpreter, SIPLRuntimeError, StepLimitExceeded
from sipl.parser import parse_ast
from sipl.trace import ExecutionTrace


def test_trace_records_all_required_kinds():
    trace = ExecutionTrace()
    interpreter = Interpreter(trace=trace)
    result = interpreter.execute(parse_ast("begin X := 2; while X > 0 do X := X - 1 end"))
    assert result == {"X": 0}
    kinds = [e.kind for e in trace.events]
    assert {"before_statement", "after_statement", "variable_changed", "condition_checked", "completed"} <= set(kinds)
    assert [e.details["result"] for e in trace.events if e.kind == "condition_checked"] == [True, True, False]
    changes = [e for e in trace.events if e.kind == "variable_changed"]
    assert [(e.details["old_value"], e.details["new_value"]) for e in changes] == [(None, 2), (2, 1), (1, 0)]
    assert trace.events[-1].state == result
    assert all(e.span is not None and e.span.line >= 1 for e in trace.events)


def test_trace_preserves_history_snapshots():
    trace = ExecutionTrace()
    interpreter = Interpreter(trace=trace)
    interpreter.execute(parse_ast("begin X := 1; X := 2 end"))
    change_states = [e.state for e in trace.events if e.kind == "variable_changed"]
    assert change_states == [{"X": 1}, {"X": 2}]
    interpreter.state["X"] = 100
    assert change_states == [{"X": 1}, {"X": 2}]


def test_trace_matches_execution_without_trace():
    program = parse_ast("if 2 > 1 then X := 3 else X := 4")
    trace = ExecutionTrace()
    traced = Interpreter(trace=trace)
    plain = Interpreter()
    assert traced.execute(program) == plain.execute(program)
    assert traced.steps == plain.steps


def test_trace_failed_runtime_reports_error():
    trace = ExecutionTrace()
    with pytest.raises(SIPLRuntimeError):
        Interpreter(trace=trace).execute(parse_ast("X := Y"))
    assert trace.events[-1].kind == "error"
    assert "Undefined variable" in trace.events[-1].details["message"]


def test_trace_failed_step_limit_reports_error():
    trace = ExecutionTrace()
    with pytest.raises(StepLimitExceeded):
        Interpreter(trace=trace, max_steps=4).execute(parse_ast("while 1 = 1 do skip"))
    assert trace.events[-1].kind == "error"


def test_trace_json_is_serializable():
    trace = ExecutionTrace()
    Interpreter(trace=trace).execute(parse_ast("skip"))
    data = json.loads(json.dumps(trace.to_json_data()))
    assert data[-1]["kind"] == "completed"
    assert data[-1]["span"]["line"] == 1


def test_trace_does_not_record_when_not_enabled():
    interpreter = Interpreter()
    assert interpreter.execute(parse_ast("X := 1")) == {"X": 1}
    assert interpreter.trace is None


@pytest.mark.parametrize("flag", ["--trace", "--trace-json"])
def test_cli_trace_modes(tmp_path, flag):
    file = tmp_path / "demo.sipl"
    file.write_text("begin X := 2; X := X + 3 end", encoding="utf-8")
    proc = subprocess.run([sys.executable, "-m", "sipl.cli", str(file), flag],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    if flag == "--trace-json":
        obj = json.loads(proc.stdout)
        assert obj["final_state"] == {"X": 5}
        assert obj["events"][-1]["kind"] == "completed"
    else:
        assert "variable_changed" in proc.stdout
        assert "Final state:" in proc.stdout
