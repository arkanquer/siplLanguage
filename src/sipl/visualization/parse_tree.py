"""VIS-01: source-linked concrete SIPL parse-tree exporters.

Outputs: text, JSON, Graphviz DOT, and Graphviz SVG (requires ``dot``).
The concrete tree uses the same course-facing grammar as the main parser,
but preserves all explicit punctuation/keyword tokens for visualization.
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from lark import Lark, Token, Tree
from lark.exceptions import UnexpectedInput

from sipl.parser import GRAMMAR_FILE, format_syntax_error


@lru_cache(maxsize=1)
def _visual_parser() -> Lark:
    return Lark(GRAMMAR_FILE.read_text(encoding="utf-8"), parser="lalr",
                propagate_positions=True, keep_all_tokens=True)


def parse_concrete(source: str) -> Tree:
    """Parse with the *same* SIPL grammar, retaining keyword/punctuation tokens."""
    return _visual_parser().parse(source)


def _span(node: Tree | Token) -> dict[str, int]:
    pos = node.meta if isinstance(node, Tree) else node
    return {"line": pos.line, "column": pos.column,
            "end_line": pos.end_line, "end_column": pos.end_column}


def tree_to_json(node: Tree | Token, *, source: str | None = None) -> dict:
    """Stable hierarchy with source positions and original token spellings."""
    if isinstance(node, Token):
        return {"kind": "token", "type": node.type, "value": str(node),
                "span": _span(node)}
    return {"kind": "rule", "name": str(node.data), "span": _span(node),
            "children": [tree_to_json(child) for child in node.children]}


def tree_to_text(node: Tree | Token, indent: int = 0) -> str:
    label = str(node.data) if isinstance(node, Tree) else f"{node.type}: {str(node)!r}"
    span = _span(node)
    line = "  " * indent + f"{label} [{span['line']}:{span['column']}-{span['end_line']}:{span['end_column']}]"
    if isinstance(node, Token):
        return line
    return "\n".join([line, *[tree_to_text(child, indent + 1) for child in node.children]])


def _dot_quote(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def tree_to_dot(node: Tree | Token) -> str:
    lines = ["digraph SIPL_ParseTree {", '  graph [rankdir=TB, bgcolor="transparent"];',
             '  node [fontname="Helvetica", fontsize=11, style="rounded,filled", shape=box];',
             '  edge [color="#94a3b8"];']
    counter = 0

    def visit(current: Tree | Token, parent: str | None = None) -> None:
        nonlocal counter
        name = f"n{counter}"
        counter += 1
        span = _span(current)
        place = f"{span['line']}:{span['column']}–{span['end_line']}:{span['end_column']}"
        if isinstance(current, Tree):
            label = f"{current.data}\n{place}"
            style = 'fillcolor="#dbeafe", color="#60a5fa", fontcolor="#172554"'
        else:
            label = f"{current.type}: {str(current)}\n{place}"
            style = 'fillcolor="#dcfce7", color="#4ade80", fontcolor="#14532d"'
        lines.append(f"  {name} [label={_dot_quote(label)}, {style}];")
        if parent is not None:
            lines.append(f"  {parent} -> {name};")
        if isinstance(current, Tree):
            for child in current.children:
                visit(child, name)

    visit(node)
    lines.append("}")
    return "\n".join(lines) + "\n"


def tree_to_svg(node: Tree | Token) -> str:
    dot_bin = shutil.which("dot")
    if dot_bin is None:
        raise RuntimeError("Graphviz `dot` not found. Install Graphviz (macOS: brew install graphviz).")
    result = subprocess.run([dot_bin, "-Tsvg"], input=tree_to_dot(node),
                            capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Graphviz failed: {result.stderr.strip()}")
    return result.stdout


def main(argv: list[str] | None = None) -> int:
    arg = argparse.ArgumentParser(prog="python -m sipl.visualization.parse_tree",
                                  description="Visualize SIPL concrete syntax trees")
    arg.add_argument("file", type=Path)
    arg.add_argument("--format", choices=["text", "json", "dot", "svg"], default="text")
    arg.add_argument("--output", type=Path, help="Write to file (default: stdout)")
    args = arg.parse_args(argv)
    try:
        source = args.file.read_text(encoding="utf-8")
        tree = parse_concrete(source)
        if args.format == "text":
            result = tree_to_text(tree) + "\n"
        elif args.format == "json":
            result = json.dumps(tree_to_json(tree), indent=2, ensure_ascii=False) + "\n"
        elif args.format == "dot":
            result = tree_to_dot(tree)
        else:
            result = tree_to_svg(tree)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result, encoding="utf-8")
            print(f"Wrote {args.format.upper()} to {args.output}")
        else:
            print(result, end="")
        return 0
    except UnexpectedInput as error:
        print(format_syntax_error(error, source), file=sys.stderr)
        return 1
    except (OSError, UnicodeError, RuntimeError) as error:
        print(f"VIS-01 error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
