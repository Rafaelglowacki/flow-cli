import json
import pytest
from flow_cli.output import emit, fail


def test_emit_json_dict(capsys):
    data = {"status": "ok", "count": 1}
    emit(data, as_json=True)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == data


def test_emit_json_list(capsys):
    data = [{"id": "1", "name": "foo"}, {"id": "2", "name": "bar"}]
    emit(data, as_json=True)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == data


def test_emit_table_dict_without_columns(capsys):
    data = {"name": "Projeto Alpha", "status": "active"}
    emit(data, as_json=False)
    captured = capsys.readouterr()
    lines = [line.strip() for line in captured.out.strip().splitlines()]
    assert "name: Projeto Alpha" in lines
    assert "status: active" in lines


def test_emit_table_list(capsys):
    data = [
        {"id": "p1", "name": "Alpha", "credits": 10},
        {"id": "p20", "name": "Beta Long Name", "credits": 5},
    ]
    emit(data, as_json=False, table_columns=["id", "name", "credits"])
    captured = capsys.readouterr()
    out = captured.out
    assert "ID" in out or "id" in out
    assert "p1" in out
    assert "p20" in out
    assert "Beta Long Name" in out


def test_fail_text(capsys):
    with pytest.raises(SystemExit) as exc_info:
        fail("ocorreu um erro", as_json=False, code=1)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "ocorreu um erro" in captured.err or "ocorreu um erro" in captured.out


def test_fail_json(capsys):
    with pytest.raises(SystemExit) as exc_info:
        fail("falha de autenticacao", as_json=True, code=2)
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    raw = captured.out or captured.err
    parsed = json.loads(raw)
    assert parsed == {"error": "falha de autenticacao"}
