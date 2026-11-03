import json
from pathlib import Path
from click.testing import CliRunner
import pytest
from flow_cli.cli import main
from flow_cli.config import profile_dir, get_backend
from flow_cli.backend import Backend
from flow_cli.browser_utils import (
    FlowError,
    wait_for_selector,
    click_by_text,
    safe_text,
)


class FakeBackend(Backend):
    def __init__(self, logged_in: bool = False):
        self._logged_in = logged_in
        self.login_opened = False
        self.closed = False
        self.logout_called = False

    def is_logged_in(self) -> bool:
        return self._logged_in

    def open_login(self) -> None:
        self.login_opened = True
        self._logged_in = True

    def logout(self) -> None:
        self.logout_called = True
        self._logged_in = False

    def close(self) -> None:
        self.closed = True


def test_profile_dir_default_and_env(monkeypatch, tmp_path):
    monkeypatch.delenv("FLOW_CLI_PROFILE_DIR", raising=False)
    default_dir = profile_dir()
    assert default_dir == Path.home() / ".config" / "flow-cli" / "profile"

    custom_dir = tmp_path / "custom_profile"
    monkeypatch.setenv("FLOW_CLI_PROFILE_DIR", str(custom_dir))
    assert profile_dir() == custom_dir


def test_auth_status_not_logged_in(monkeypatch):
    fake = FakeBackend(logged_in=False)
    runner = CliRunner()
    result = runner.invoke(main, ["auth", "status"], obj={"backend": fake})
    assert result.exit_code == 0
    assert "Não logado" in result.output or "não logado" in result.output.lower()


def test_auth_status_logged_in(monkeypatch):
    fake = FakeBackend(logged_in=True)
    runner = CliRunner()
    result = runner.invoke(main, ["auth", "status"], obj={"backend": fake})
    assert result.exit_code == 0
    assert "Logado" in result.output or "logado" in result.output.lower()


def test_auth_status_json(monkeypatch):
    fake = FakeBackend(logged_in=True)
    runner = CliRunner()
    result = runner.invoke(main, ["--json", "auth", "status"], obj={"backend": fake})
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed == {"logged_in": True}

    fake_off = FakeBackend(logged_in=False)
    result_off = runner.invoke(main, ["--json", "auth", "status"], obj={"backend": fake_off})
    assert result_off.exit_code == 0
    assert json.loads(result_off.output) == {"logged_in": False}


def test_auth_login_flow():
    fake = FakeBackend(logged_in=False)
    runner = CliRunner()
    result = runner.invoke(main, ["auth", "login"], obj={"backend": fake})
    assert result.exit_code == 0
    assert fake.login_opened is True
    assert fake.closed is True
    assert "sucesso" in result.output.lower() or "logado" in result.output.lower()


def test_auth_login_json():
    fake = FakeBackend(logged_in=False)
    runner = CliRunner()
    result = runner.invoke(main, ["--json", "auth", "login"], obj={"backend": fake})
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed.get("logged_in") is True


def test_auth_logout_requires_yes(monkeypatch, tmp_path):
    p_dir = tmp_path / "profile"
    p_dir.mkdir(parents=True)
    (p_dir / "state.json").write_text("{}")
    monkeypatch.setenv("FLOW_CLI_PROFILE_DIR", str(p_dir))

    fake = FakeBackend(logged_in=True)
    runner = CliRunner()
    result = runner.invoke(main, ["auth", "logout"], obj={"backend": fake})
    # Sem --yes, deve falhar ou avisar e não apagar
    assert result.exit_code != 0
    assert p_dir.exists()
    assert fake.logout_called is False


def test_auth_logout_with_yes_removes_profile(monkeypatch, tmp_path):
    p_dir = tmp_path / "profile"
    p_dir.mkdir(parents=True)
    (p_dir / "cookie.bin").write_text("dummy")
    monkeypatch.setenv("FLOW_CLI_PROFILE_DIR", str(p_dir))

    fake = FakeBackend(logged_in=True)
    runner = CliRunner()
    result = runner.invoke(main, ["auth", "logout", "--yes"], obj={"backend": fake})
    assert result.exit_code == 0
    assert not p_dir.exists()
    assert fake.logout_called is True


def test_auth_logout_json(monkeypatch, tmp_path):
    p_dir = tmp_path / "profile"
    p_dir.mkdir(parents=True)
    monkeypatch.setenv("FLOW_CLI_PROFILE_DIR", str(p_dir))

    fake = FakeBackend(logged_in=True)
    runner = CliRunner()
    result = runner.invoke(main, ["--json", "auth", "logout", "--yes"], obj={"backend": fake})
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed.get("logged_out") is True
