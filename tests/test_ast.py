import pytest
from lark.exceptions import UnexpectedInput
from sipl.ast import Assignment, BinaryOp, Block, Comparison, If, Number, Skip, Variable, While
from sipl.parser import format_syntax_error, parse, parse_ast

def test_assignment_and_number_spans():
    node = parse_ast("X := 123")
    assert isinstance(node, Assignment)
    assert node.name == "X"
    assert isinstance(node.expression, Number)
    assert node.expression.value == 123
    assert (node.span.line, node.span.column, node.span.end_column) == (1, 1, 9)
    assert (node.expression.span.column, node.expression.span.end_column) == (6, 9)


def test_operator_precedence():
    node = parse_ast("X := 1 + 2 * 3")
    expr = node.expression
    assert isinstance(expr, BinaryOp) and expr.operator == "+"
    assert isinstance(expr.right, BinaryOp) and expr.right.operator == "*"
    assert expr.right.left.value == 2


def test_parentheses_override_precedence():
    node = parse_ast("X := (1 + 2) * 3")
    assert node.expression.operator == "*"
    assert node.expression.left.operator == "+"


def test_block_sequence_and_while():
    node = parse_ast("begin\n X := 2;\n while X > 0 do X := X - 1\nend")
    assert isinstance(node, Block)
    assert len(node.statements) == 2
    loop = node.statements[1]
    assert isinstance(loop, While)
    assert isinstance(loop.condition, Comparison)
    assert loop.condition.operator == ">"
    assert isinstance(loop.condition.left, Variable)
    assert isinstance(loop.body, Assignment)
    assert loop.span.line == 3


def test_if_else_and_skip():
    node = parse_ast("if X <= 10 then skip else X := 10")
    assert isinstance(node, If)
    assert node.condition.operator == "<="
    assert isinstance(node.then_branch, Skip)
    assert isinstance(node.else_branch, Assignment)


def test_existing_parse_tree_is_preserved():
    assert parse("X := 1").data == "assignment"


def test_diagnostic_shows_position():
    source = "begin\n X :=\nend"
    with pytest.raises(UnexpectedInput) as caught:
        parse_ast(source)
    message = format_syntax_error(caught.value, source)
    assert "line 3, column 1" in message
    assert "end" in message
