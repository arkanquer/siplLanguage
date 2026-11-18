from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

from lark import Lark, Token, Transformer, v_args
from lark.exceptions import UnexpectedInput

from .ast import Assignment, BinaryOp, Block, Comparison, If, Number, Skip, SourceSpan, Variable, While
from .interpreter import Interpreter, SIPLRuntimeError
from .trace import ExecutionTrace


@lru_cache(maxsize=1)
def get_course_parser() -> Lark:
    path = Path(__file__).resolve().parent / "grammar" / "course.lark"
    return Lark(path.read_text(encoding="utf-8"), parser="lalr", propagate_positions=True)


def parse_course(source: str):
    return get_course_parser().parse(source)


def _span(meta):
    return SourceSpan(meta.line, meta.column, meta.end_line, meta.end_column)


def _token_span(token: Token):
    return SourceSpan(token.line, token.column, token.end_line, token.end_column)


@v_args(meta=True)
class CourseTransformer(Transformer):
    def number(self, meta, children):
        token = children[0]
        return Number(int(token), _token_span(token))

    def variable(self, meta, children):
        token = children[0]
        return Variable(str(token), _token_span(token))

    def unary_minus(self, meta, children):
        return BinaryOp("-", Number(0, _span(meta)), children[0], _span(meta))

    def grouped_arithmetic(self, meta, children):
        return children[0]

    def _binary(self, meta, children, symbol):
        return BinaryOp(symbol, children[0], children[1], _span(meta))

    def add(self, meta, children):
        return self._binary(meta, children, "+")

    def subtract(self, meta, children):
        return self._binary(meta, children, "-")

    def multiply(self, meta, children):
        return self._binary(meta, children, "*")

    def equal(self, meta, children):
        return Comparison(children[0], "=", children[1], _span(meta))

    def greater(self, meta, children):
        return Comparison(children[0], ">", children[1], _span(meta))

    def negate(self, meta, children):
        return LogicalNot(children[0], _span(meta))

    def grouped_condition(self, meta, children):
        return children[0]

    def disjunction(self, meta, children):
        if len(children) == 1:
            return children[0]
        left = children[0]
        for right in children[1:]:
            left = LogicalOr(left, right, _span(meta))
        return left

    def assignment(self, meta, children):
        return Assignment(str(children[0]), children[1], _span(meta))

    def skip(self, meta, children):
        return Skip(_span(meta))

    def sequence(self, meta, children):
        if len(children) == 1:
            return children[0]
        return Block(list(children), _span(meta))

    def block(self, meta, children):
        node = children[0]
        return Block(node.statements if isinstance(node, Block) else [node], _span(meta))

    def program(self, meta, children):
        node = children[0]
        return Block(node.statements if isinstance(node, Block) else [node], _span(meta))

    def if_else(self, meta, children):
        return If(children[0], children[1], children[2], _span(meta))

    def while_loop(self, meta, children):
        return While(children[0], children[1], _span(meta))


from .ast import LogicalNot, LogicalOr


def parse_course_ast(source: str):
    return CourseTransformer().transform(parse_course(source))


def run_course(source: str, *, initial_state=None, max_steps=10_000):
    return Interpreter(initial_state, max_steps=max_steps).execute(parse_course_ast(source))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m sipl.course")
    parser.add_argument("action", choices=["check", "parse", "run", "trace"])
    parser.add_argument("file", type=Path)
    parser.add_argument("--max-steps", type=int, default=10000)
    args = parser.parse_args(argv)
    source = args.file.read_text(encoding="utf-8")
    try:
        tree = parse_course(source)
        if args.action == "check":
            print("Syntax OK (course SIPL)")
        elif args.action == "parse":
            print(tree.pretty())
        else:
            ast = CourseTransformer().transform(tree)
            trace = ExecutionTrace() if args.action == "trace" else None
            runner = Interpreter(max_steps=args.max_steps, trace=trace)
            state = runner.execute(ast)
            if trace is not None:
                print(json.dumps({"state": state, "events": [asdict(e) for e in trace.events]}, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
    except UnexpectedInput as exc:
        print(f"Syntax error, line {exc.line}, column {exc.column}\n{exc.get_context(source)}")
        return 2
    except SIPLRuntimeError as exc:
        print(str(exc))
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
