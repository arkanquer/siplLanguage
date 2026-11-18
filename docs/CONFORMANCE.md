# CORE-06 — SIPL Conformance Suite (format v1)

This is a **separate, implementation-neutral test suite** for the SIPL subset implemented in this project. Tests are stored as files, *not* tied to `Interpreter` or `ASTTransformer` Python classes. The runner calls a candidate executable via a documented CLI/JSON interface. The candidate can be implemented in another language.

## Run

From the project root, after `python -m pip install -e '.[dev]'`:

```sh
python conformance/run_suite.py
python conformance/run_suite.py --command sipl
pytest -q
```

`--command` accepts one quoted command string; e.g. `--command "python -m sipl.cli"`. Success is exit code 0; mismatch is exit code 1; empty fixture directory gives exit code 2. The suite runner requires only Python standard library.

## Files and schema

Each `conformance/cases/NAME.json` corresponds to `NAME.sipl` in the same folder. JSON schema version 1 uses:

```json
{
  "schema_version": 1,
  "id": "assignment",
  "source": "assignment.sipl",
  "expect": {
    "outcome": "success",
    "ast": {"type": "Assignment", "name": "X", "expression": {"type": "Number", "value": 7}},
    "final_state": {"X": 7}
  }
}
```

Errors instead use `{"outcome":"error", "phase":"check", "error":{"code":"SYNTAX_ERROR", "line":1}}` or `phase: "run", code: "RUNTIME_ERROR"`. Optional top-level `max_steps` controls a step-limit test (default 10,000). Source filenames are relative to the cases directory.

## Candidate CLI/JSON protocol

A conforming implementation supports these invocations, returning **one valid JSON object on stdout**:

- `CANDIDATE parse FILE --json`: success `{"ok":true,"ast":{...}}` and exit 0.
- `CANDIDATE run FILE --json --max-steps N`: success `{"ok":true,"final_state":{...}}` and exit 0.
- `CANDIDATE check FILE --json`: syntax errors return nonzero exit and `{"ok":false,"diagnostics":[{"code":"SYNTAX_ERROR","span":{"line":1}}]}`.
- Runtime errors return nonzero exit and `{"ok":false,"diagnostics":[{"code":"RUNTIME_ERROR","span":{"line":1}}]}`.

The runner intentionally **ignores AST source-coordinate fields** (`span`) when checking structure because spans are orthogonal to abstract syntax; source location is explicitly checked for diagnostics. AST nodes are identified by their standard `type` field (`Assignment`, `Number`, `Variable`, `BinaryOp`, `Comparison`, `Skip`, `Block`, `If`, `While`). For compatibility with the current CORE-05 CLI, the runner can infer these types from field names if `type` is omitted. Expected AST snapshots are checked recursively, including operator precedence, branches, and nested blocks. The runner checks `final_state` as an exact mapping.

## Scope and limitations

17 fixtures currently exercise correct programs, invalid syntax, undefined variables, division by zero and nonterminating loops. This is a finite, repeatable conformance suite — **not a proof** of equivalence for all SIPL programs. Integer division semantics reflect the project's existing interpreter. The language grammar remains a working draft until confirmed against the course's precise SIPL BNF.
