from __future__ import annotations
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any
from lark.exceptions import LarkError, UnexpectedInput
from .ast import SourceSpan
from .interpreter import Interpreter, SIPLRuntimeError
from .parser import format_syntax_error, parse, parse_ast
from .trace import ExecutionTrace

EXIT_OK = 0
EXIT_PROGRAM_ERROR = 1
EXIT_IO_ERROR = 2

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sipl", description="SIPL language toolkit")
    subcommands = parser.add_subparsers(dest="command")
    for name in ("parse", "check", "run", "trace"):
        cmd = subcommands.add_parser(name, help=f"{name} a SIPL file")
        cmd.add_argument("file", type=Path)
        cmd.add_argument("--json", action="store_true", help="Emit a single JSON document")
        if name in ("run", "trace"):
            cmd.add_argument("--max-steps", type=int, default=10_000)
    return parser


def _legacy_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sipl", description="Legacy CLI compatibility")
    parser.add_argument("file", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--ast", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--trace", action="store_true")
    modes.add_argument("--trace-json", action="store_true")
    parser.add_argument("--max-steps", type=int, default=10_000)
    return parser


def _emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _failure(kind: str, message: str, *, span: Any = None,
             is_json: bool = False, code: int = EXIT_PROGRAM_ERROR) -> int:
    diagnostic = {"code": kind, "message": message,
                  "span": asdict(span) if span is not None else None}
    if is_json:
        _emit_json({"ok": False, "diagnostics": [diagnostic]})
    else:
        print(f"ERROR [{kind}]: {message}")
    return code


def _execute(command: str, file: Path, *, is_json: bool = False,
             max_steps: int = 10_000, legacy: bool = False,
             legacy_tree: bool = False, legacy_ast: bool = False) -> int:
    try:
        source = file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return _failure("IO_ERROR", str(exc), is_json=is_json, code=EXIT_IO_ERROR)

    if command in ("run", "trace") and max_steps <= 0:
        return _failure("INVALID_ARGUMENT", "max_steps must be positive", is_json=is_json,
                        code=EXIT_IO_ERROR)

    try:
        if command == "check":
            parse(source)
            if is_json:
                _emit_json({"ok": True, "command": "check", "diagnostics": []})
            else:
                print("Syntax OK")
            return EXIT_OK

        if command == "parse":
            if legacy_tree:
                tree = parse(source)
                print("Syntax OK")
                print(tree.pretty())
                return EXIT_OK
            node = parse_ast(source)
            if is_json:
                _emit_json({"ok": True, "command": "parse", "ast": asdict(node),
                            "diagnostics": []})
            elif legacy_ast:
                print("Syntax OK")
                _emit_json(asdict(node))
            else:
                _emit_json(asdict(node))
            return EXIT_OK

        ast = parse_ast(source)
        trace = ExecutionTrace() if command == "trace" else None
        interpreter = Interpreter(max_steps=max_steps, trace=trace)
        state = interpreter.execute(ast)
        if is_json and not legacy:
            payload: dict[str, Any] = {"ok": True, "command": command,
                                       "final_state": state, "steps": interpreter.steps,
                                       "diagnostics": []}
            if command == "trace":
                payload["events"] = trace.to_json_data()
            _emit_json(payload)
        elif command == "trace" and is_json:
            _emit_json({"final_state": state, "events": trace.to_json_data()})
        elif command == "trace":
            for event in trace.events:
                loc = f"{event.span.line}:{event.span.column}" if event.span else "-"
                print(f"[{event.step:>3}] {loc:<7} {event.kind:<19} "
                      f"{event.details} state={event.state}")
            print("Final state:", state)
        else:
            print("Final state:")
            for name, value in sorted(state.items()):
                print(f"{name} = {value}")
            print("Execution completed successfully.")
        return EXIT_OK
    except UnexpectedInput as exc:
        return _failure("SYNTAX_ERROR", format_syntax_error(exc, source),
                        is_json=is_json,
                        span=SourceSpan(exc.line, exc.column, exc.line, exc.column + 1))
    except SIPLRuntimeError as exc:
        return _failure("RUNTIME_ERROR", str(exc), span=exc.span, is_json=is_json)
    except (LarkError, ValueError) as exc:
        return _failure("PROGRAM_ERROR", str(exc), is_json=is_json)


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if args_list and args_list[0] in ("parse", "check", "run", "trace"):
        args = _parser().parse_args(args_list)
        return _execute(args.command, args.file, is_json=args.json,
                        max_steps=getattr(args, "max_steps", 10_000))
    if args_list and args_list[0] in ("-h", "--help"):
        _parser().parse_args(args_list)
        return EXIT_OK
    if not args_list:
        _parser().print_help()
        return EXIT_IO_ERROR
    args = _legacy_parser().parse_args(args_list)
    command = "trace" if (args.trace or args.trace_json) else ("run" if args.run else "parse")
    return _execute(command, args.file, is_json=args.trace_json,
                    max_steps=args.max_steps, legacy=True,
                    legacy_tree=not any((args.ast, args.run, args.trace, args.trace_json)),
                    legacy_ast=args.ast)

if __name__ == "__main__":
    raise SystemExit(main())
