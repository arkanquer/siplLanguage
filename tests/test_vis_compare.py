import json
from pathlib import Path

from sipl.visualization.compare import comparison_data, comparison_html, main


def _walk(node):
    yield node
    for child in node['children']:
        yield from _walk(child)


def test_distinct_concrete_and_abstract_trees():
    data = comparison_data('begin X := 5 + 3; skip end')
    concrete = list(_walk(data['parse_tree']))
    abstract = list(_walk(data['ast']))
    assert any('BEGIN' in node['label'].upper() for node in concrete)
    assert any('Assignment: X' in node['label'] for node in abstract)
    assert not any('BEGIN:' in node['label'].upper() for node in abstract)
    assert len(concrete) > len(abstract)


def test_positions_appear_in_both_views():
    data = comparison_data('X := 7')
    assert data['parse_tree']['span']['line'] == 1
    assert data['ast']['span']['column'] == 1
    assert all(node['span']['end_column'] >= 1 for node in _walk(data['ast']))


def test_nested_while_ast():
    data = comparison_data('begin X := 2; while X > 0 do X := X - 1 end')
    assert {'Block', 'While', 'Comparison: >', 'BinaryOp: -'} <= {
        node['label'] for node in _walk(data['ast'])
    }


def test_html_is_self_contained_and_interactive():
    html = comparison_html('X := 1')
    assert '<!doctype html>' in html
    assert 'Parse Tree' in html and 'AST' in html
    assert 'chooseMatch' in html and 'highlight(node)' in html
    assert '<script type="application/json" id="model">' in html


def test_html_escapes_program_text():
    html = comparison_html('if X < 4 then skip else skip')
    assert 'X &lt; 4' not in html  # program is stored as safely escaped JSON, not raw markup
    assert '\\u003c' in html


def test_json_export(tmp_path):
    source = tmp_path / 'program.sipl'
    source.write_text('X := 3', encoding='utf-8')
    dest = tmp_path / 'data.json'
    assert main([str(source), '--json', '--output', str(dest)]) == 0
    model = json.loads(dest.read_text(encoding='utf-8'))
    assert model['source'] == 'X := 3'
    assert model['ast']['label'] == 'Assignment: X'


def test_html_export(tmp_path):
    source = tmp_path / 'program.sipl'
    source.write_text('skip', encoding='utf-8')
    dest = tmp_path / 'view.html'
    assert main([str(source), '--output', str(dest)]) == 0
    assert 'Parse Tree' in dest.read_text(encoding='utf-8')


def test_invalid_source(tmp_path, capsys):
    source = tmp_path / 'bad.sipl'
    source.write_text('X = 1', encoding='utf-8')
    assert main([str(source), '--output', str(tmp_path / 'view.html')]) == 1
    assert 'Syntax error' in capsys.readouterr().err
