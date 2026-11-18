"""VIS-02: source-linked, interactive Parse Tree ↔ typed AST comparison.

Generates a standalone HTML file. Both views originate from the same source
and the existing core parsers, with no duplicate grammar or execution engine.
"""
from __future__ import annotations

import argparse
from dataclasses import fields, is_dataclass
import html
import json
from pathlib import Path
import sys

from lark import Token, Tree
from lark.exceptions import UnexpectedInput

from sipl.parser import format_syntax_error, parse_ast
from sipl.visualization.parse_tree import parse_concrete, _span as concrete_span


def _span_dict(span: object) -> dict[str, int]:
    return {k: int(getattr(span, k)) for k in ("line", "column", "end_line", "end_column")}


def _flatten(node: object, mode: str, ids: list[int]) -> dict:
    """Normalize either source-derived tree to a shared UI node shape."""
    ids[0] += 1
    node_id = f"{mode}{ids[0]}"
    if mode == "p":
        if isinstance(node, Tree):
            label = str(node.data)
            children = [_flatten(x, mode, ids) for x in node.children]
        elif isinstance(node, Token):
            label = f"{node.type}: {str(node)}"
            children = []
        else:
            raise TypeError(f"Unexpected parse node {type(node).__name__}")
        span = concrete_span(node)
    else:
        if not is_dataclass(node):
            raise TypeError(f"Unexpected AST node {type(node).__name__}")
        cls = type(node).__name__
        if cls == "Assignment":
            label = f"Assignment: {node.name}"
        elif cls == "Variable":
            label = f"Variable: {node.name}"
        elif cls == "Number":
            label = f"Number: {node.value}"
        elif cls in ("Comparison", "BinaryOp"):
            label = f"{cls}: {node.operator}"
        else:
            label = cls
        children = []
        for fld in fields(node):
            if fld.name == "span":
                continue
            value = getattr(node, fld.name)
            if is_dataclass(value):
                children.append(_flatten(value, mode, ids))
            elif isinstance(value, list):
                children.extend(_flatten(item, mode, ids) for item in value if is_dataclass(item))
        span = _span_dict(node.span)
    return {"id": node_id, "label": label, "span": span, "children": children}


def comparison_data(source: str) -> dict:
    """Public, JSON-serializable comparison model for other tools."""
    parse_tree = parse_concrete(source)
    ast = parse_ast(source)
    return {
        "source": source,
        "parse_tree": _flatten(parse_tree, "p", [0]),
        "ast": _flatten(ast, "a", [0]),
    }


def _tree_markup(node: dict) -> str:
    title = html.escape(node["label"])
    span = node["span"]
    coords = f"{span['line']}:{span['column']}–{span['end_line']}:{span['end_column']}"
    children = "".join(f"<li>{_tree_markup(child)}</li>" for child in node["children"])
    return (f'<div class="node"><button type="button" data-id="{node["id"]}" '
            f'title="{html.escape(coords)}">{title}</button>'
            f'<small>{html.escape(coords)}</small></div>'
            + (f'<ul>{children}</ul>' if children else ""))


def comparison_html(source: str) -> str:
    """Create a portable HTML comparison with synchronized source highlighting."""
    data = comparison_data(source)
    p = _tree_markup(data["parse_tree"])
    a = _tree_markup(data["ast"])
    payload = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c")
    return """<!doctype html>
<html lang="uk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SIPL • Parse Tree ↔ AST</title>
<style>
:root{font:15px system-ui,-apple-system,sans-serif;color:#15243b;background:#f3f6fb}
*{box-sizing:border-box}body{margin:0 auto;max-width:1500px;padding:24px}
h1{margin:0 0 6px;font-size:25px}p{margin:0 0 18px;color:#52627b}
main{display:grid;grid-template-columns:minmax(250px,1fr) minmax(250px,1fr);gap:16px}
section{background:white;border:1px solid #dae3ef;border-radius:12px;padding:16px;min-width:0}
h2{font-size:17px;margin:0 0 12px}.tree{max-height:540px;overflow:auto}
ul{margin:3px 0 4px 17px;padding:0;border-left:1px solid #ccd7e8;list-style:none}
li{margin:5px 0 5px 8px}.node{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
button{border:1px solid #c6d7ef;background:#eef5ff;color:#244473;cursor:pointer;padding:5px 9px;border-radius:7px;text-align:left}
button:hover{background:#dceaff}button.selected{background:#245aca;color:white;border-color:#245aca}
button.related{background:#e0f8e9;color:#17633b;border-color:#83d3a0}
small{font-size:11px;color:#78859b}pre{white-space:pre-wrap;word-break:break-word;line-height:1.65;margin:0}
#source{font:13px/1.65 ui-monospace,SFMono-Regular,Consolas,monospace}
mark{background:#f9d76b;border-radius:2px} .source-card{margin-top:16px}
@media(max-width:780px){main{grid-template-columns:1fr}}
</style></head><body>
<h1>SIPL • Parse Tree ↔ AST</h1>
<p>Натисни будь-який вузол: буде виділено фрагмент коду й відповідний вузол іншого дерева (за діапазоном тексту).</p>
<main><section><h2>Parse Tree · конкретний синтаксис</h2><div class="tree"><ul><li>""" + p + """</li></ul></div></section>
<section><h2>AST · абстрактний синтаксис</h2><div class="tree"><ul><li>""" + a + """</li></ul></div></section></main>
<section class="source-card"><h2>Вихідна SIPL-програма</h2><pre id="source"></pre></section>
<script type="application/json" id="model">""" + payload + """</script>
<script>
'use strict';
const model = JSON.parse(document.getElementById('model').textContent);
const sourceElement = document.getElementById('source');
const source = model.source;
const nodes = new Map();
const groups = {p:[], a:[]};
function collect(node){nodes.set(node.id,node); groups[node.id[0]].push(node); node.children.forEach(collect);}
collect(model.parse_tree);collect(model.ast);
const lines = source.split('\\n');
function offset(line,column){
  let result=0;
  for(let i=0;i<line-1;i++)result+=lines[i].length+1;
  return result+column-1;
}
function range(node){const s=node.span;return [offset(s.line,s.column),offset(s.end_line,s.end_column)];}
function highlight(node){
  const [start,end]=range(node);sourceElement.replaceChildren();
  sourceElement.append(document.createTextNode(source.slice(0,start)));
  const mark=document.createElement('mark');mark.textContent=source.slice(start,end);
  sourceElement.append(mark,document.createTextNode(source.slice(end)));
}
function chooseMatch(node){
  const [start,end]=range(node), others=groups[node.id[0]==='p'?'a':'p'];
  let selected=null, best=-Infinity;
  for(const other of others){
    const [a,b]=range(other);const overlap=Math.max(0,Math.min(end,b)-Math.max(start,a));
    const contains=a<=start&&b>=end;
    const score=(contains?100000:0)+overlap*100-(b-a);
    if((overlap>0||contains)&&score>best){best=score;selected=other;}
  }
  return selected;
}
function select(id){
  const node=nodes.get(id);if(!node)return;
  document.querySelectorAll('button[data-id]').forEach(b=>b.classList.remove('selected','related'));
  const active=document.querySelector(`[data-id="${id}"]`);if(active)active.classList.add('selected');
  const match=chooseMatch(node);
  if(match){const related=document.querySelector(`[data-id="${match.id}"]`);
    if(related){related.classList.add('related');related.scrollIntoView({block:'nearest'});}}
  highlight(node);
}
document.querySelectorAll('button[data-id]').forEach(b=>b.addEventListener('click',()=>select(b.dataset.id)));
sourceElement.textContent=source;
</script></body></html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare SIPL concrete and abstract syntax")
    parser.add_argument("file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("outputs/comparison.html"))
    parser.add_argument("--json", action="store_true", help="Export a structured model instead of HTML")
    args = parser.parse_args(argv)
    try:
        source = args.file.read_text(encoding="utf-8")
        result = (json.dumps(comparison_data(source), indent=2, ensure_ascii=False)
                  if args.json else comparison_html(source))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
        print(f"Wrote comparison to {args.output}")
        return 0
    except UnexpectedInput as exc:
        print(format_syntax_error(exc, source), file=sys.stderr)
        return 1
    except (OSError, UnicodeError, TypeError) as exc:
        print(f"VIS-02 error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
