#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

REQUIRED_TYPES = {'Block', 'Assignment', 'Number', 'Variable', 'BinaryOp', 'Comparison', 'If', 'While', 'Skip'}


def normalize_ast(node: Any, field: str | None = None) -> Any:
    if isinstance(node, list):
        return [normalize_ast(item) for item in node]
    if not isinstance(node, dict):
        return node
    data = {k: normalize_ast(v, k) for k, v in node.items() if k != 'span'}
    if 'statements' in data:
        kind = 'Block'
    elif 'then_branch' in data:
        kind = 'If'
    elif 'body' in data:
        kind = 'While'
    elif 'expression' in data:
        kind = 'Assignment'
    elif 'left' in data and 'right' in data:
        kind = 'Comparison' if field == 'condition' else 'BinaryOp'
    elif 'name' in data:
        kind = 'Variable'
    elif 'value' in data:
        kind = 'Number'
    elif data == {}:
        kind = 'Skip'
    else:
        raise ValueError(f'Unknown AST node structure: {list(data)}')
    return {'type': kind, **data}


def validate_case(fixture: dict[str, Any], base: Path) -> None:
    if fixture.get('schema_version') != 1:
        raise ValueError('Unsupported schema_version')
    if not isinstance(fixture.get('id'), str) or not fixture['id']:
        raise ValueError('Case must have id')
    source = fixture.get('source')
    if not isinstance(source, str) or Path(source).name != source or not source.endswith('.sipl'):
        raise ValueError('Case source must be a local .sipl filename')
    if not (base / source).is_file():
        raise ValueError(f'Missing source file: {source}')
    expect = fixture.get('expect', {})
    if expect.get('outcome') not in ('success', 'error'):
        raise ValueError('Invalid expected outcome')
    if expect['outcome'] == 'success':
        if not isinstance(expect.get('ast'), dict) or not isinstance(expect.get('final_state'), dict):
            raise ValueError('Successful case must define ast and final_state')
    else:
        if expect.get('phase') not in ('check', 'run') or not isinstance(expect.get('error'), dict):
            raise ValueError('Error case must specify phase and error')
        if not isinstance(expect['error'].get('code'), str):
            raise ValueError('Error code must be a string')
    if not isinstance(fixture.get('max_steps', 10000), int) or fixture.get('max_steps', 10000) <= 0:
        raise ValueError('max_steps must be a positive integer')


def invoke(command: list[str], action: str, source: Path, max_steps: int) -> tuple[int, dict[str, Any]]:
    argv = [*command, action, str(source), '--json']
    if action == 'run':
        argv.extend(['--max-steps', str(max_steps)])
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=12, check=False)
    except subprocess.TimeoutExpired as error:
        raise AssertionError('Candidate process timed out') from error
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(f'Expected JSON on stdout, got {proc.stdout[:180]!r}; stderr={proc.stderr[:180]!r}') from error
    if not isinstance(result, dict):
        raise AssertionError('CLI JSON response must be an object')
    return proc.returncode, result


def run_case(fixture: dict[str, Any], base: Path, command: list[str]) -> None:
    validate_case(fixture, base)
    expected = fixture['expect']
    source = base / fixture['source']
    max_steps = fixture.get('max_steps', 10000)
    if expected['outcome'] == 'success':
        code, parsed = invoke(command, 'parse', source, max_steps)
        if code != 0 or parsed.get('ok') is not True:
            raise AssertionError(f'Parse failed: exit={code}, data={parsed}')
        actual_ast = normalize_ast(parsed.get('ast'))
        if actual_ast != expected['ast']:
            raise AssertionError(f'AST mismatch\nexpected={json.dumps(expected["ast"],ensure_ascii=False)}\nactual={json.dumps(actual_ast,ensure_ascii=False)}')
        code, result = invoke(command, 'run', source, max_steps)
        if code != 0 or result.get('ok') is not True:
            raise AssertionError(f'Run failed: exit={code}, data={result}')
        if result.get('final_state') != expected['final_state']:
            raise AssertionError(f'State mismatch: expected {expected["final_state"]}, got {result.get("final_state")}')
    else:
        code, result = invoke(command, expected['phase'], source, max_steps)
        if code == 0 or result.get('ok') is not False:
            raise AssertionError(f'Expected a nonzero exit and ok=false; got exit={code} data={result}')
        diagnostics = result.get('diagnostics', [])
        if not isinstance(diagnostics, list) or not diagnostics:
            raise AssertionError('Expected at least one diagnostic')
        diagnostic = diagnostics[0]
        if diagnostic.get('code') != expected['error']['code']:
            raise AssertionError(f'Diagnostic code mismatch: {diagnostic}')
        if 'line' in expected['error']:
            span = diagnostic.get('span')
            if not isinstance(span, dict) or span.get('line') != expected['error']['line']:
                raise AssertionError(f'Diagnostic location mismatch: {diagnostic}')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run implementation-neutral SIPL conformance fixtures')
    parser.add_argument('--cases', type=Path, default=Path(__file__).resolve().parent / 'cases')
    parser.add_argument('--command', type=str, default=f'{sys.executable} -m sipl.cli', help='Candidate CLI executable and optional arguments (default: python -m sipl.cli)')
    args = parser.parse_args(argv)
    fixtures = sorted(args.cases.glob('*.json'))
    if not fixtures:
        print('No conformance cases found', file=sys.stderr)
        return 2
    passed = 0
    for path in fixtures:
        try:
            fixture = json.loads(path.read_text(encoding='utf-8'))
            run_case(fixture, args.cases, shlex.split(args.command))
            passed += 1
            print(f'PASS {fixture["id"]}')
        except (OSError, ValueError, AssertionError) as error:
            print(f'FAIL {path.name}: {error}')
    print(f'\nConformance: {passed}/{len(fixtures)} passed')
    return 0 if passed == len(fixtures) else 1

if __name__ == '__main__':
    raise SystemExit(main())
