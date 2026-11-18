import json
import subprocess
import sys
from pathlib import Path

import pytest
from lark import Token, Tree

from sipl.parser import parse
from sipl.visualization.parse_tree import (parse_concrete, tree_to_dot,
    tree_to_json, tree_to_svg, tree_to_text)


SOURCE = "begin X := 5; while X > 0 do X := X - 1 end"


def _tokens(tree):
    for child in tree.children:
        if isinstance(child, Token):
            yield str(child)
        elif isinstance(child, Tree):
            yield from _tokens(child)


def test_real_parser_and_visual_parser_accept_same_source():
    assert parse(SOURCE)
    assert parse_concrete(SOURCE)


def test_concrete_tree_retains_punctuation_and_keywords():
    tokens = list(_tokens(parse_concrete(SOURCE)))
    assert "begin" in tokens and ":=" in tokens and "while" in tokens
    assert ";" in tokens and "end" in tokens


def test_json_hierarchy_has_source_spans():
    doc = tree_to_json(parse_concrete(SOURCE))
    assert doc["kind"] == "rule"
    assert doc["name"] == "block"
    assert doc["span"]["line"] == 1
    assert doc["span"]["column"] == 1
    assert doc["span"]["end_column"] == len(SOURCE) + 1
    assert json.loads(json.dumps(doc)) == doc


def test_multiline_source_span():
    doc = tree_to_json(parse_concrete("begin\n X := 1\nend"))
    assert doc["span"]["end_line"] == 3


def test_text_has_positions():
    output = tree_to_text(parse_concrete(SOURCE))
    assert "block [1:1-" in output
    assert "ASSIGN" in output or ":=" in output


def test_dot_has_nodes_and_edges():
    dot = tree_to_dot(parse_concrete(SOURCE))
    assert "digraph SIPL_ParseTree" in dot
    assert "n0 -> n1" in dot
    assert "while_loop" in dot


def test_svg_generates_real_image():
    import shutil
    if shutil.which("dot") is None:
        pytest.skip("Graphviz executable unavailable")
    svg = tree_to_svg(parse_concrete(SOURCE))
    assert "<svg" in svg and "</svg>" in svg
    assert "while_loop" in svg


def test_cli_json_and_svg_file(tmp_path):
    source = tmp_path / "example.sipl"
    source.write_text(SOURCE)
    output = tmp_path / "tree.json"
    cmd = [sys.executable, "-m", "sipl.visualization.parse_tree", str(source),
           "--format", "json", "--output", str(output)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text())["name"] == "block"


def test_cli_invalid_source(tmp_path):
    source = tmp_path / "invalid.sipl"
    source.write_text("begin X := end")
    result = subprocess.run([sys.executable, "-m", "sipl.visualization.parse_tree",
                             str(source)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "Syntax error" in result.stderr


def test_cli_missing_source(tmp_path):
    result = subprocess.run([sys.executable, "-m", "sipl.visualization.parse_tree",
                             str(tmp_path / "missing.sipl")], capture_output=True, text=True)
    assert result.returncode == 2
