# SIPL Language Toolkit — Starter

## Planned task IDs: 10.0 points

CORE-01 (0.5), CORE-02 (1.5), CORE-03 (2.0), CORE-04 (1.0), CORE-05 (1.0), CORE-06 (1.0), VIS-01 (1.5), VIS-02 (1.0), REL-01 (0.5).

**Current state:** CORE-01 draft, CORE-02 typed AST, CORE-03 interpreter, CORE-04 trace and CORE-05 CLI implemented and tested. The project is **not** a completed 10-point project; the course BNF and semantics still need verification.

## Install (macOS, Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Run

```bash
python -m sipl.cli examples/multiplication.sipl
pytest -q
```

## Course-alignment TODO

The project brief says the course's SIPL BNF is authoritative, but the full grammar is not reproduced in the brief. This starter uses a **provisional working grammar** matching its core examples and commonly expected SIPL forms. Before declaring CORE-01 complete, compare each rule against the actual practical manual BNF, adjust the syntax, and document any language extensions.

## Next modules

- CORE-01: verify provisional grammar against the exact course BNF and revise as needed.
- CORE-04/05: implemented; retain regression and CLI contract tests.
- VIS-01/02: separate source-linked parse tree and AST views.
- CORE-06: implementation-independent conformance fixtures.
- REL-01: CI with lint, type-check, test and build.

## CORE-02: Typed AST (implemented for the working grammar)

`parse(source)` returns the Lark parse tree; `parse_ast(source)` returns our own
`Assignment`, `Block`, `While`, `If`, `Skip`, `Number`, `Variable`, `BinaryOp`, and
`Comparison` dataclasses. Nodes contain `SourceSpan` with 1-based line and column
coordinates, and end positions are exclusive.

```bash
python -m sipl.cli examples/multiplication.sipl --ast
pytest -v
```

`--ast` prints a JSON representation of the AST. This is a development output;
CORE-05 stable JSON API is not yet implemented. The language grammar is still a
working draft pending alignment with the exact course BNF.

## CORE-03: Interpreter

`src/sipl/interpreter.py` evaluates the typed AST and returns the final mapping
from variable names to integer values. It supports assignment, composition,
`if/then/else`, `while/do`, `begin/end`, `skip`, arithmetic and comparisons.
Undefined variables, division by zero, and exceeding the execution step budget
are explicit runtime errors with source locations.

```bash
python -m sipl.cli examples/multiplication.sipl --run
python -m sipl.cli examples/multiplication.sipl --run --max-steps 100
pytest -q
pytest --cov=sipl --cov-report=term-missing
```

The standalone runtime API is:

```python
from sipl.interpreter import run, Interpreter
print(run("begin X := 2; X := X + 3 end"))  # {'X': 5}
print(Interpreter({'Y': 4}).execute(parse_ast('X := Y * 2')))
```

**Current semantics are provisional** until checked against the course SIPL
specification. Integer division (`/`) truncates toward zero; variable reads
before assignment raise an error. A step counts every statement visit and
`while` condition test. This version adds `--run` as a development flag, but
the full stable `parse/check/run/trace` CLI for CORE-05 is not complete.

## CORE-04: Execution trace

Capture immutable snapshots of state, event type, source span, step index, and metadata:

```bash
python -m sipl.cli examples/multiplication.sipl --trace
python -m sipl.cli examples/multiplication.sipl --trace-json
pytest -q
```

Events: `before_statement`, `after_statement`, `variable_changed`, `condition_checked`, `completed`, `error`.
`ExecutionTrace` collects events in memory; `Interpreter(trace=trace)` enables collection.
`--trace-json` is a development format; the stable CORE-05 schema and CLI commands are forthcoming.

## CORE-05 CLI (version 0.1)

Install the project again after updating its `pyproject.toml`:

```bash
python -m pip install -e '.[dev]'
sipl check examples/multiplication.sipl
sipl parse examples/multiplication.sipl --json
sipl run examples/multiplication.sipl --json
sipl trace examples/multiplication.sipl --json
sipl trace examples/multiplication.sipl --max-steps 100
pytest -q
```

The CLI is also available as `python -m sipl.cli` and legacy forms such as
`python -m sipl.cli examples/multiplication.sipl --trace-json` still work.

### JSON v0.1 contract

Successful responses always contain `ok: true`, `command`, and `diagnostics: []`.
`parse` returns `ast` (with recursive `span` coordinates), `check` validates
syntax, `run` returns `final_state` and `steps`, and `trace` adds `events`.
Failed requests output `{"ok": false, "diagnostics": [{"code": "...", "message": "...", "span": null}]}`;
the `span` is an object when available. `SYNTAX_ERROR`, `RUNTIME_ERROR`,
`IO_ERROR`, and `INVALID_ARGUMENT` are stable diagnostic codes.

Exit status: `0` success, `1` source syntax/runtime error, `2` IO/configuration
error or argparse usage error. JSON goes to stdout as a single document.
The legacy `--trace-json` response is kept as originally defined without an
`ok` wrapper for backwards compatibility.

The authoritative grammar for the installed Python package is
`src/sipl/grammar/sipl.lark`; `grammar/sipl.lark` is its course-facing copy.
Keep the two copies synchronized whenever changing the SIPL syntax.

## CORE-06: standalone conformance suite (1.0 point)

The `conformance/` folder is a portable, executable set of **17 fixtures** covering
syntax, complete typed AST structure (without spans), final variable state and
expected syntax/runtime failures. Its `run_suite.py` uses **only Python's standard
library**, runs the language implementation as an external subprocess via the
CORE-05 command-line JSON protocol, and does not import the project's parser
or runtime internals. See [docs/CONFORMANCE.md](docs/CONFORMANCE.md) for the
fixture format, CLI contract, and limitations.

```bash
python conformance/run_suite.py
python conformance/run_suite.py --command 'python -m sipl.cli'
pytest -q
```

The suite reports `17/17 passed` on this project's implementation. It can
also run against another implementation exposing the same CLI contract.

## VIS-01: concrete parse tree export (1.5 points)

The visualization uses the **same grammar** as CORE-01/02, with `keep_all_tokens=True`
so concrete syntax includes `begin`, `end`, `:=`, semicolons, etc. Every rule and
token carries a 1-based source span (end-exclusive). No hardcoded trees.

```bash
python -m sipl.visualization.parse_tree examples/multiplication.sipl --format text
python -m sipl.visualization.parse_tree examples/multiplication.sipl --format json --output outputs/parse_tree.json
python -m sipl.visualization.parse_tree examples/multiplication.sipl --format dot --output outputs/parse_tree.dot
python -m sipl.visualization.parse_tree examples/multiplication.sipl --format svg --output outputs/parse_tree.svg
pytest -q
```

SVG requires the external **Graphviz** `dot` executable (`brew install graphviz` on Mac).
DOT, Text, and JSON require no extra dependencies. Source spans annotate each
node; JSON children preserve full rule/token hierarchy. This is the concrete
parse tree, **not** the compact typed AST; comparison will be in VIS-02.

## VIS-02 — Interactive Parse Tree ↔ AST comparison (1.0 point)

Generate a self-contained HTML view (no web server required):

```bash
python -m sipl.visualization.compare examples/multiplication.sipl --output outputs/comparison.html
open outputs/comparison.html  # macOS
```

Click a node in either tree to highlight its source range and the closest corresponding
node in the opposite tree. Parse Tree keeps concrete keyword/punctuation tokens;
AST consists only of typed semantic nodes. Selection correspondence is based on
source ranges and can be approximate for wrapper nodes.

For integration, a JSON comparison model is also available:

```bash
python -m sipl.visualization.compare examples/multiplication.sipl --json --output outputs/comparison.json
```

Run focused checks: `pytest -q tests/test_vis_compare.py`.

## REL-01 — GitHub Actions CI (0.5 point)

CI runs on every pull request and each push to `main`/`master`. The workflow is
in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) and uses Python 3.12
and 3.14. It installs the package, performs restricted Ruff checks for syntax/
undefined-name errors, uses mypy to type-check the annotated AST and trace
models, runs pytest and the independent conformance suite, then builds wheel
and source distributions. The Python 3.12 job uploads `dist/` as an artifact.

**CI coverage limitations:** Ruff checks critical errors rather than enforcing
full style; mypy covers `ast.py` and `trace.py` rather than all application
modules. Expanding coverage is a future quality improvement; do not describe
this as full-project static verification.

Local equivalents:

```bash
python -m pip install -e '.[dev]'
python -m pip install 'ruff>=0.9,<1' 'mypy>=1.14,<2' 'build>=1.2,<2' wheel
ruff check --select E4,E7,E9,F821,F822,F823 src tests conformance
mypy --follow-imports=silent --ignore-missing-imports src/sipl/ast.py src/sipl/trace.py
python -m pytest -q -k "not test_all_conformance_fixtures"
python conformance/run_suite.py
python -m build --no-isolation
```

GitHub verification: commit and push `.github/workflows/ci.yml` to your repo,
open the **Actions** tab, and inspect the **SIPL CI** run. Then create a pull
request to verify the PR trigger. A successful local test is not proof that a
GitHub-hosted workflow has passed; confirm the green run before claiming REL-01.

The pytest wrapper `test_all_conformance_fixtures` is intentionally excluded in CI
because the full independent conformance runner runs immediately afterward.
Other conformance unit tests remain enabled.

## Автоматична перевірка

Проєкт перевіряється за допомогою GitHub Actions.