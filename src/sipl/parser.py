"""Lark concrete parse tree and typed SIPL AST with source coordinates."""
from functools import lru_cache
from pathlib import Path

from lark import Lark, Token, Transformer, Tree, v_args
from lark.exceptions import UnexpectedInput

from .ast import Assignment, BinaryOp, Block, Comparison, If, Number, Skip, SourceSpan, Variable, While, Statement

GRAMMAR_FILE = Path(__file__).resolve().parent / "grammar" / "sipl.lark"


@lru_cache(maxsize=1)
def get_parser() -> Lark:
    return Lark(
        GRAMMAR_FILE.read_text(encoding="utf-8"),
        parser="lalr",
        propagate_positions=True,
    )


def parse(source: str) -> Tree:
    """Return the Lark concrete parse tree (retained for CORE-01/VIS-01)."""
    return get_parser().parse(source)


def _span(meta) -> SourceSpan:
    return SourceSpan(meta.line, meta.column, meta.end_line, meta.end_column)


def _token_span(token: Token) -> SourceSpan:
    return SourceSpan(token.line, token.column, token.end_line, token.end_column)


@v_args(meta=True)
class ASTTransformer(Transformer):
    """Convert Lark's syntax rules into our own typed nodes."""

    def number(self, meta, children):
        token = children[0]
        return Number(int(token), _token_span(token))

    def variable(self, meta, children):
        token = children[0]
        return Variable(str(token), _token_span(token))

    def _binary(self, meta, children, op):
        return BinaryOp(op, children[0], children[1], _span(meta))

    def add(self, meta, children):
        return self._binary(meta, children, "+")

    def subtract(self, meta, children):
        return self._binary(meta, children, "-")

    def multiply(self, meta, children):
        return self._binary(meta, children, "*")

    def divide(self, meta, children):
        return self._binary(meta, children, "/")

    def comparison(self, meta, children):
        return Comparison(children[0], str(children[1]), children[2], _span(meta))

    def assignment(self, meta, children):
        return Assignment(str(children[0]), children[1], _span(meta))

    def skip(self, meta, children):
        return Skip(_span(meta))

    def statement_list(self, meta, children):
        return list(children)

    def block(self, meta, children):
        return Block(children[0], _span(meta))

    def if_else(self, meta, children):
        return If(children[0], children[1], children[2], _span(meta))

    def while_loop(self, meta, children):
        return While(children[0], children[1], _span(meta))


def parse_ast(source: str) -> Statement:
    """Parse SIPL source and return a typed AST; raises Lark syntax errors."""
    return ASTTransformer().transform(parse(source))


def format_syntax_error(error: UnexpectedInput, source: str) -> str:
    """Create a human-readable diagnostic with source line and column."""
    return (f"Syntax error at line {error.line}, column {error.column}:\n"
            f"{error.get_context(source, span=35).rstrip()}")
