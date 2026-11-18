"""Tests for the independent, subprocess-driven conformance distribution."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'conformance' / 'run_suite.py'

spec = importlib.util.spec_from_file_location('sipl_conformance_runner', RUNNER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_all_conformance_fixtures():
    assert module.main(['--cases', str(ROOT / 'conformance' / 'cases'),
                        '--command', f'{sys.executable} -m sipl.cli']) == 0


def test_no_cases_is_failure(tmp_path):
    assert module.main(['--cases', str(tmp_path)]) == 2


def test_reject_missing_source(tmp_path):
    case = {'schema_version': 1, 'id': 'invalid', 'source': 'missing.sipl',
            'expect': {'outcome': 'success', 'ast': {}, 'final_state': {}}}
    try:
        module.validate_case(case, tmp_path)
    except ValueError as error:
        assert 'Missing source file' in str(error)
    else:
        raise AssertionError('Case unexpectedly accepted')


def test_normalizer_keeps_structure_and_ignores_spans():
    node = {'name': 'X', 'expression': {'value': 1, 'span': {'line': 1}}, 'span': {'line': 1}}
    assert module.normalize_ast(node) == {'type': 'Assignment', 'name': 'X',
                                          'expression': {'type': 'Number', 'value': 1}}


def test_detects_incorrect_expected_state(tmp_path):
    (tmp_path / 'simple.sipl').write_text('X := 3\n')
    case = {'schema_version': 1, 'id': 'wrong', 'source': 'simple.sipl',
            'expect': {'outcome': 'success',
                       'ast': {'type': 'Assignment', 'name': 'X', 'expression': {'type': 'Number', 'value': 3}},
                       'final_state': {'X': 999}}}
    try:
        module.run_case(case, tmp_path, [sys.executable, '-m', 'sipl.cli'])
    except AssertionError as error:
        assert 'State mismatch' in str(error)
    else:
        raise AssertionError('Mismatch was not caught')
