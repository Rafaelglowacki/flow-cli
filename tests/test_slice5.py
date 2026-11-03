from pathlib import Path
import json
import re
from unittest.mock import MagicMock
import pytest
from click.testing import CliRunner
from flow_cli.cli import main
from flow_cli.backend import Backend, PlaywrightBackend
from flow_cli.browser_utils import FlowError
from flow_cli.parsers import project_url


# --- Fake Backend for CLI tests ---
class Slice5FakeBackend(Backend):
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.closed = False
        self.created_projects = []
        self.downloaded_media = []

    def is_logged_in(self) -> bool:
        return True

    def open_login(self) -> None:
        pass

    def logout(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    def get_credits(self) -> dict:
        return {"credits": 100, "reset": None}

    def create_project(self, name: str | None = None) -> dict:
        if self.should_fail:
            raise FlowError("erro ao criar projeto")
        proj_id = "12345678-1234-1234-1234-123456789abc"
        res = {
            "id": proj_id,
            "title": name or "nov. 03 - 15:49",
            "url": f"https://flow.google.com/project/{proj_id}",
        }
        self.created_projects.append((name, res))
        return res

    def download_media(self, media_id: str, out_dir: Path, project_id: str | None = None) -> dict:
        if self.should_fail:
            raise FlowError("mídia não encontrada")
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / f"{media_id}.jpg"
        file_path.write_bytes(b"fake-image-bytes")
        res = {
            "id": media_id,
            "path": str(file_path),
            "bytes": len(b"fake-image-bytes"),
            "kind": "image",
        }
        self.downloaded_media.append((media_id, out_dir, project_id, res))
        return res


# --- Tests for project_url helper ---
def test_project_url_valid_uuids():
    valid_uuid = "12345678-1234-1234-1234-123456789abc"
    expected = f"https://flow.google.com/project/{valid_uuid}"
    assert project_url(valid_uuid) == expected
    assert project_url(valid_uuid.upper()) == f"https://flow.google.com/project/{valid_uuid.upper()}"


def test_project_url_invalid_uuid():
    with pytest.raises(FlowError, match="inválido"):
        project_url("invalid-uuid")

    with pytest.raises(FlowError, match="inválido"):
        project_url("../traversal")

    with pytest.raises(FlowError, match="inválido"):
        project_url("")


def test_backend_base_methods_raise_not_supported(tmp_path):
    class ConcreteBackend(Backend):
        def is_logged_in(self) -> bool:
            return True
        def open_login(self) -> None:
            pass
        def logout(self) -> None:
            pass
        def close(self) -> None:
            pass

    backend = ConcreteBackend()
    with pytest.raises(FlowError, match="não suportado"):
        backend.download_media("m1", tmp_path)

    with pytest.raises(FlowError, match="não suportado"):
        backend.create_project("novo")



# --- CLI: projects create ---
def test_cli_projects_create_text():
    runner = CliRunner()
    fake = Slice5FakeBackend()
    res = runner.invoke(main, ["projects", "create", "Meu Projeto"], obj={"backend": fake})
    assert res.exit_code == 0
    assert "Projeto criado: 12345678-1234-1234-1234-123456789abc" in res.output
    assert "https://flow.google.com/project/12345678-1234-1234-1234-123456789abc" in res.output
    assert fake.created_projects[0][0] == "Meu Projeto"


def test_cli_projects_create_json():
    runner = CliRunner()
    fake = Slice5FakeBackend()
    res = runner.invoke(main, ["--json", "projects", "create", "Meu Projeto"], obj={"backend": fake})
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["id"] == "12345678-1234-1234-1234-123456789abc"
    assert data["title"] == "Meu Projeto"


def test_cli_projects_create_error():
    runner = CliRunner()
    fake = Slice5FakeBackend(should_fail=True)
    res = runner.invoke(main, ["projects", "create", "Meu Projeto"], obj={"backend": fake})
    assert res.exit_code == 1
    assert "erro ao criar projeto" in res.output


# --- CLI: projects open ---
def test_cli_projects_open_text(monkeypatch):
    runner = CliRunner()
    valid_uuid = "12345678-1234-1234-1234-123456789abc"
    res = runner.invoke(main, ["projects", "open", valid_uuid])
    assert res.exit_code == 0
    assert f"https://flow.google.com/project/{valid_uuid}" in res.output


def test_cli_projects_open_invalid_uuid():
    runner = CliRunner()
    res = runner.invoke(main, ["projects", "open", "invalid-id"])
    assert res.exit_code == 1
    assert "inválido" in res.output.lower()


def test_cli_projects_open_with_browser_flag(monkeypatch):
    runner = CliRunner()
    valid_uuid = "12345678-1234-1234-1234-123456789abc"
    mock_open = MagicMock()
    monkeypatch.setattr("webbrowser.open", mock_open)

    res = runner.invoke(main, ["projects", "open", valid_uuid, "--browser"])
    assert res.exit_code == 0
    expected_url = f"https://flow.google.com/project/{valid_uuid}"
    assert expected_url in res.output
    mock_open.assert_called_once_with(expected_url)


def test_cli_projects_open_json():
    runner = CliRunner()
    valid_uuid = "12345678-1234-1234-1234-123456789abc"
    res = runner.invoke(main, ["--json", "projects", "open", valid_uuid])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["id"] == valid_uuid
    assert data["url"] == f"https://flow.google.com/project/{valid_uuid}"


# --- CLI: media download ---
def test_cli_media_download_text(tmp_path):
    runner = CliRunner()
    fake = Slice5FakeBackend()
    res = runner.invoke(
        main,
        ["media", "download", "m-123", "--out", str(tmp_path), "--project", "p-abc"],
        obj={"backend": fake},
    )
    assert res.exit_code == 0
    assert "Baixado:" in res.output
    assert str(tmp_path / "m-123.jpg") in res.output
    assert fake.downloaded_media[0][0] == "m-123"
    assert fake.downloaded_media[0][1] == tmp_path
    assert fake.downloaded_media[0][2] == "p-abc"


def test_cli_media_download_default_out(tmp_path, monkeypatch):
    runner = CliRunner()
    fake = Slice5FakeBackend()
    monkeypatch.chdir(tmp_path)
    res = runner.invoke(main, ["media", "download", "m-default"], obj={"backend": fake})
    assert res.exit_code == 0
    assert "Baixado:" in res.output
    expected_default_dir = tmp_path / "flow-downloads"
    assert fake.downloaded_media[0][1] == expected_default_dir


def test_cli_media_download_json(tmp_path):
    runner = CliRunner()
    fake = Slice5FakeBackend()
    res = runner.invoke(
        main,
        ["--json", "media", "download", "m-123", "--out", str(tmp_path)],
        obj={"backend": fake},
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["id"] == "m-123"
    assert data["kind"] == "image"
    assert data["bytes"] > 0
    assert data["path"] == str(tmp_path / "m-123.jpg")


def test_cli_media_download_error(tmp_path):
    runner = CliRunner()
    fake = Slice5FakeBackend(should_fail=True)
    res = runner.invoke(
        main,
        ["media", "download", "m-notfound", "--out", str(tmp_path)],
        obj={"backend": fake},
    )
    assert res.exit_code == 1
    assert "mídia não encontrada" in res.output


# --- CLI: REPL ---
def test_repl_basic_execution_and_exit():
    runner = CliRunner()
    fake = Slice5FakeBackend()
    # Executa credits e depois exit
    result = runner.invoke(main, ["repl"], input="credits\nexit\n", obj={"backend": fake})
    assert result.exit_code == 0
    assert "flow> " in result.output
    assert "Créditos: 100" in result.output


def test_repl_empty_lines_and_quit():
    runner = CliRunner()
    fake = Slice5FakeBackend()
    result = runner.invoke(main, ["repl"], input="\n  \nquit\n", obj={"backend": fake})
    assert result.exit_code == 0
    assert "flow> " in result.output


def test_repl_eof():
    runner = CliRunner()
    fake = Slice5FakeBackend()
    result = runner.invoke(main, ["repl"], input="", obj={"backend": fake})
    assert result.exit_code == 0
    assert "flow> " in result.output


def test_repl_help():
    runner = CliRunner()
    fake = Slice5FakeBackend()
    result = runner.invoke(main, ["repl"], input="help\nexit\n", obj={"backend": fake})
    assert result.exit_code == 0
    assert "flow - CLI não oficial para o Google Flow" in result.output
    assert "projects" in result.output
    assert "media" in result.output


def test_repl_unknown_command_does_not_crash():
    runner = CliRunner()
    fake = Slice5FakeBackend()
    result = runner.invoke(main, ["repl"], input="invalidcommandfoo\ncredits\nexit\n", obj={"backend": fake})
    assert result.exit_code == 0
    assert "Créditos: 100" in result.output


def test_repl_recursive_forbidden():
    runner = CliRunner()
    fake = Slice5FakeBackend()
    result = runner.invoke(main, ["repl"], input="repl\nexit\n", obj={"backend": fake})
    assert result.exit_code == 0
    assert "não é permitido executar 'repl' dentro do repl" in result.output.lower()


def test_repl_global_json():
    runner = CliRunner()
    fake = Slice5FakeBackend()
    result = runner.invoke(main, ["--json", "repl"], input="credits\nexit\n", obj={"backend": fake})
    assert result.exit_code == 0
    assert '"credits": 100' in result.output


# --- Unit tests for PlaywrightBackend.create_project & download_media mocks ---
def test_playwright_backend_create_project(tmp_path):
    backend = PlaywrightBackend(profile_path=tmp_path)
    mock_page = MagicMock()
    mock_page.url = "https://flow.google.com/project/11111111-2222-3333-4444-555555555555"

    btn_new = MagicMock()
    mock_page.get_by_role.side_effect = lambda role, name=None, **kwargs: btn_new if name == "Novo projeto" else MagicMock()

    backend._goto = MagicMock()
    backend._ensure_browser = MagicMock(return_value=mock_page)

    res = backend.create_project(name="Meu Projeto Playwright")
    assert res["id"] == "11111111-2222-3333-4444-555555555555"
    assert res["title"] == "Meu Projeto Playwright"
    assert "11111111-2222-3333-4444-555555555555" in res["url"]


def test_playwright_backend_download_media_image(tmp_path):
    backend = PlaywrightBackend(profile_path=tmp_path)
    mock_page = MagicMock()
    mock_context = MagicMock()
    backend._context = mock_context
    backend._ensure_browser = MagicMock(return_value=mock_page)
    backend._goto = MagicMock()

    # Locator for media element
    mock_img = MagicMock()
    mock_img.count.return_value = 1
    mock_img.first = mock_img
    mock_img.get_attribute.side_effect = lambda attr: "https://flow.google.com/asb/abcdef=s512-rw" if attr == "src" else None

    # Card / group
    mock_group = MagicMock()
    mock_img.locator.return_value = mock_group
    mock_group.locator.return_value.count.return_value = 0  # no video tag

    mock_page.locator.side_effect = lambda sel: mock_img if 'img[data-media-id="m1"]' in sel else MagicMock()

    # Mock context.request.get
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.headers = {"content-type": "image/jpeg"}
    mock_response.body.return_value = b"real-image-bytes"
    mock_context.request.get.return_value = mock_response

    res = backend.download_media(media_id="m1", out_dir=tmp_path, project_id="p1")
    assert res["id"] == "m1"
    assert res["kind"] == "image"
    assert res["bytes"] == len(b"real-image-bytes")
    expected_path = tmp_path / "m1.jpg"
    assert res["path"] == str(expected_path)
    assert expected_path.read_bytes() == b"real-image-bytes"
    mock_context.request.get.assert_called_once_with("https://flow.google.com/asb/abcdef=d")


def test_playwright_backend_download_media_not_found(tmp_path):
    backend = PlaywrightBackend(profile_path=tmp_path)
    mock_page = MagicMock()
    backend._ensure_browser = MagicMock(return_value=mock_page)
    backend._goto = MagicMock()
    backend.list_projects = MagicMock(return_value=[{"id": "p1"}])

    mock_img = MagicMock()
    mock_img.count.return_value = 0
    mock_page.locator.return_value = mock_img

    with pytest.raises(FlowError, match="não encontrada"):
        backend.download_media(media_id="m-missing", out_dir=tmp_path)
