from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class SourceSpan:
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass(frozen=True)
class Number:
    value: int
    span: SourceSpan


@dataclass(frozen=True)
class Variable:
    name: str
    span: SourceSpan


@dataclass(frozen=True)
class BinaryOp:
    operator: str
    left: Expression
    right: Expression
    span: SourceSpan


Expression = Number | Variable | BinaryOp


@dataclass(frozen=True)
class Comparison:
    left: Expression
    operator: str
    right: Expression
    span: SourceSpan


@dataclass(frozen=True)
class Assignment:
    name: str
    expression: Expression
    span: SourceSpan


@dataclass(frozen=True)
class Skip:
    span: SourceSpan


@dataclass(frozen=True)
class Block:
    statements: list[Statement]
    span: SourceSpan


@dataclass(frozen=True)
class If:
    condition: Comparison
    then_branch: Statement
    else_branch: Statement
    span: SourceSpan


@dataclass(frozen=True)
class While:
    condition: Comparison
    body: Statement
    span: SourceSpan

Statement = Assignment | Skip | Block | If | While
