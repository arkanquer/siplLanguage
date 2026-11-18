import json
import subprocess
import sys
import pytest


def invoke(*args):
    return subprocess.run([sys.executable, "-m", "sipl.cli", *map(str, args)],
                          capture_output=True, text=True)

@pytest.fixture
def program(tmp_path):
    path = tmp_path / "valid.sipl"
    path.write_text("begin X := 2; Y := X + 4 end", encoding="utf-8")
    return path

@pytest.mark.parametrize("cmd", ["parse", "check", "run", "trace"])
def test_all_commands(program, cmd):
    result = invoke(cmd, program)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("cmd", ["parse", "check", "run", "trace"])
def test_json_modes(program, cmd):
    result = invoke(cmd, program, "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True and payload["command"] == cmd
    assert payload["diagnostics"] == []
    if cmd == "parse":
        assert payload["ast"]["statements"][0]["name"] == "X"
    if cmd in ("run", "trace"):
        assert payload["final_state"] == {"X": 2, "Y": 6}
    if cmd == "trace":
        assert payload["events"][-1]["kind"] == "completed"

def test_syntax_error_json(tmp_path):
    path = tmp_path / "bad.sipl"
    path.write_text("X = 2", encoding="utf-8")
    result = invoke("check", path, "--json")
    assert result.returncode == 1
    diag = json.loads(result.stdout)["diagnostics"][0]
    assert diag["code"] == "SYNTAX_ERROR"
    assert diag["span"]["line"] == 1

def test_runtime_error_json(tmp_path):
    path = tmp_path / "runtime.sipl"
    path.write_text("X := Y", encoding="utf-8")
    result = invoke("run", path, "--json")
    assert result.returncode == 1
    diag = json.loads(result.stdout)["diagnostics"][0]
    assert diag["code"] == "RUNTIME_ERROR" and diag["span"]["line"] == 1

def test_missing_file():
    result = invoke("parse", "/missing/does-not-exist.sipl", "--json")
    assert result.returncode == 2
    assert json.loads(result.stdout)["diagnostics"][0]["code"] == "IO_ERROR"

def test_step_limit(tmp_path):
    path = tmp_path / "loop.sipl"
    path.write_text("while 1 = 1 do skip", encoding="utf-8")
    result = invoke("run", path, "--max-steps", "5", "--json")
    assert result.returncode == 1
    assert "step limit" in json.loads(result.stdout)["diagnostics"][0]["message"]

def test_invalid_max_steps(program):
    result = invoke("trace", program, "--max-steps", "0", "--json")
    assert result.returncode == 2
    assert json.loads(result.stdout)["diagnostics"][0]["code"] == "INVALID_ARGUMENT"

def test_command_help():
    result = invoke("--help")
    assert result.returncode == 0
    assert "parse" in result.stdout and "trace" in result.stdout