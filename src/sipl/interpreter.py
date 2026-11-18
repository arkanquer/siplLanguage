from __future__ import annotations

from collections.abc import Mapping

from .ast import Assignment, BinaryOp, Block, Comparison, Expression, If, Number, Skip, SourceSpan, Statement, Variable, While
from .trace import ExecutionTrace
from .ast import Condition, LogicalNot, LogicalOr


class SIPLRuntimeError(Exception):
    """Execution error with an optional source location."""

    def __init__(self, message: str, span: SourceSpan | None = None):
        self.message = message
        self.span = span
        location = f"line {span.line}, column {span.column}: " if span else ""
        super().__init__(location + message)


class StepLimitExceeded(SIPLRuntimeError):
    pass

class Interpreter:
    def __init__(self, initial_state: Mapping[str, int] | None = None, *, max_steps: int = 10_000,
                 trace: ExecutionTrace | None = None):
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        self.state = dict(initial_state or {})
        if any(not isinstance(k, str) or not isinstance(v, int) or isinstance(v, bool)
               for k, v in self.state.items()):
            raise ValueError("Initial state must map variable names to integers")
        self.max_steps = max_steps
        self.steps = 0
        self.trace = trace

    def _emit(self, kind: str, span: SourceSpan | None, **details: object) -> None:
        if self.trace is not None:
            self.trace.record(kind, self.steps, span, self.state, **details)

    def _step(self, span: SourceSpan) -> None:
        if self.steps >= self.max_steps:
            raise StepLimitExceeded(f"Execution step limit exceeded ({self.max_steps})", span)
        self.steps += 1

    def evaluate(self, expr: Expression) -> int:
        if isinstance(expr, Number):
            return expr.value
        if isinstance(expr, Variable):
            if expr.name not in self.state:
                raise SIPLRuntimeError(f"Undefined variable '{expr.name}'", expr.span)
            return self.state[expr.name]
        if isinstance(expr, BinaryOp):
            left = self.evaluate(expr.left)
            right = self.evaluate(expr.right)
            if expr.operator == "+":
                return left + right
            if expr.operator == "-":
                return left - right
            if expr.operator == "*":
                return left * right
            if expr.operator == "/":
                if right == 0:
                    raise SIPLRuntimeError("Division by zero", expr.span)
                quotient = abs(left) // abs(right)
                return -quotient if (left < 0) != (right < 0) else quotient
            raise SIPLRuntimeError(f"Unknown arithmetic operator '{expr.operator}'", expr.span)
        raise SIPLRuntimeError(f"Unsupported expression: {type(expr).__name__}")

    def check(self, expr: Condition) -> bool:
        if isinstance(expr, LogicalNot):
            return not self.check(expr.operand)
        if isinstance(expr, LogicalOr):
            return self.check(expr.left) or self.check(expr.right)
        left = self.evaluate(expr.left)
        right = self.evaluate(expr.right)
        return {
            "=": lambda: left == right,"!=": lambda: left != right,
            "<": lambda: left < right,"<=": lambda: left <= right,
            ">": lambda: left > right,">=": lambda: left >= right,
        }[expr.operator]()

    def execute(self, node: Statement) -> dict[str, int]:
        try:
            self._execute(node)
        except SIPLRuntimeError as exc:
            self._emit("error", exc.span, message=str(exc))
            raise
        self._emit("completed", node.span)
        return dict(self.state)

    def _execute(self, node: Statement) -> None:
        self._step(node.span)
        self._emit("before_statement", node.span, statement=type(node).__name__)
        if isinstance(node, Assignment):
            value = self.evaluate(node.expression)
            previous = self.state.get(node.name)
            self.state[node.name] = value
            self._emit("variable_changed", node.span, variable=node.name,
                       old_value=previous, new_value=value, was_defined=previous is not None)
        elif isinstance(node, Skip):
            pass
        elif isinstance(node, Block):
            for statement in node.statements:
                self._execute(statement)
        elif isinstance(node, If):
            condition = self.check(node.condition)
            self._emit("condition_checked", node.condition.span, result=condition,
                       construct="if")
            self._execute(node.then_branch if condition else node.else_branch)
        elif isinstance(node, While):
            while True:
                self._step(node.condition.span)
                condition = self.check(node.condition)
                self._emit("condition_checked", node.condition.span, result=condition,
                           construct="while")
                if not condition:
                    break
                self._execute(node.body)
        else:
            raise SIPLRuntimeError(f"Unsupported statement: {type(node).__name__}", node.span)
        self._emit("after_statement", node.span, statement=type(node).__name__)


def run(source: str, *, initial_state: Mapping[str, int] | None = None,
        max_steps: int = 10_000) -> dict[str, int]:
    from .parser import parse_ast
    return Interpreter(initial_state, max_steps=max_steps).execute(parse_ast(source))
