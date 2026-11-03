"""Integração ao vivo, somente leitura. Opt-in: FLOW_CLI_LIVE=1 pytest -m live."""
import json
import os

import pytest
from click.testing import CliRunner

from flow_cli.cli import main

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("FLOW_CLI_LIVE") != "1", reason="defina FLOW_CLI_LIVE=1"),
]


def _run(*args):
    res = CliRunner().invoke(main, ["--json", *args])
    assert res.exit_code == 0, res.output
    return json.loads(res.output)


def test_live_auth_status():
    assert _run("auth", "status")


def test_live_credits():
    assert _run("credits")


def test_live_projects_list():
    assert isinstance(_run("projects", "list"), (list, dict))


def test_live_models_list():
    assert _run("models", "list")


def test_live_media_list():
    assert isinstance(_run("media", "list"), (list, dict))
