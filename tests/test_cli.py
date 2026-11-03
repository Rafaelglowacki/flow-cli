import json
from click.testing import CliRunner
from flow_cli.cli import main
from flow_cli import __version__


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help_lists_all_groups():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    groups_and_commands = [
        "auth",
        "projects",
        "models",
        "credits",
        "media",
        "generate",
        "repl",
    ]
    for item in groups_and_commands:
        assert item in result.output


def test_stub_json_error():
    runner = CliRunner()
    result = runner.invoke(main, ["--json", "credits"])
    assert result.exit_code == 2
    parsed = json.loads(result.output)
    assert "error" in parsed
    assert "não implementado" in parsed["error"].lower()


def test_stubs_auth_and_projects():
    runner = CliRunner()
    res_auth = runner.invoke(main, ["--json", "auth", "login"])
    assert res_auth.exit_code == 2
    assert "não implementado" in json.loads(res_auth.output)["error"].lower()

    res_proj = runner.invoke(main, ["--json", "projects", "list"])
    assert res_proj.exit_code == 2
    assert "não implementado" in json.loads(res_proj.output)["error"].lower()


def test_validation_generate_count_rejected():
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "image", "prompt test", "--count", "5"])
    assert result.exit_code != 0
    # Click rejection message for choice or range
    assert "5" in result.output or "Invalid value" in result.output


def test_validation_generate_duration_rejected():
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "video", "prompt test", "--duration", "7"])
    assert result.exit_code != 0
    assert "7" in result.output or "Invalid value" in result.output


def test_generate_image_help_has_yes():
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "image", "--help"])
    assert result.exit_code == 0
    assert "--yes" in result.output
    assert "créditos" in result.output or "creditos" in result.output


def test_generate_video_help_has_yes():
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "video", "--help"])
    assert result.exit_code == 0
    assert "--yes" in result.output
    assert "créditos" in result.output or "creditos" in result.output
