import json
from unittest.mock import MagicMock
import pytest
from click.testing import CliRunner
from flow_cli.cli import main
from flow_cli.backend import Backend, PlaywrightBackend
from flow_cli.browser_utils import FlowError


class GenerateFakeBackend(Backend):
    def __init__(self, cost=24, project_id="p-mock", should_fail=False):
        self.cost = cost
        self.project_id = project_id
        self.should_fail = should_fail
        self.closed = False
        self.last_generate_call = None

    def is_logged_in(self) -> bool:
        return True

    def open_login(self) -> None:
        pass

    def logout(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    def generate(
        self,
        kind: str,
        prompt: str,
        *,
        project_id: str | None = None,
        aspect: str | None = None,
        model: str | None = None,
        count: int = 1,
        resolution: str | None = None,
        duration: str | None = None,
        confirm: bool = False,
    ) -> dict:
        if self.should_fail:
            raise FlowError("Falha na geração do modelo")

        resolved_project = project_id or self.project_id
        self.last_generate_call = {
            "kind": kind,
            "prompt": prompt,
            "project_id": resolved_project,
            "aspect": aspect,
            "model": model,
            "count": count,
            "resolution": resolution,
            "duration": duration,
            "confirm": confirm,
        }

        res = {
            "kind": kind,
            "project": resolved_project,
            "model": model,
            "aspect": aspect,
            "count": count,
            "cost": self.cost,
            "submitted": confirm,
            "dry_run": not confirm,
        }
        if kind == "video":
            res["resolution"] = resolution
            res["duration"] = duration
        return res


# --- Testes de CLI ---

def test_generate_image_dry_run_text():
    fake = GenerateFakeBackend(cost=0, project_id="proj-123")
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "image", "um gato amarelo"], obj={"backend": fake})
    assert result.exit_code == 0
    assert fake.closed is True
    assert fake.last_generate_call["confirm"] is False
    assert fake.last_generate_call["prompt"] == "um gato amarelo"
    assert "Dry-run: esta geração usaria 0 créditos (projeto proj-123). Nada foi gerado. Use --yes para gerar." in result.output


def test_generate_image_dry_run_json():
    fake = GenerateFakeBackend(cost=0, project_id="proj-123")
    runner = CliRunner()
    result = runner.invoke(main, ["--json", "generate", "image", "um gato amarelo"], obj={"backend": fake})
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["submitted"] is False
    assert data["dry_run"] is True
    assert data["cost"] == 0
    assert data["project"] == "proj-123"
    assert data["kind"] == "image"


def test_generate_image_confirmed():
    fake = GenerateFakeBackend(cost=0, project_id="proj-123")
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "image", "um gato amarelo", "--yes"], obj={"backend": fake})
    assert result.exit_code == 0
    assert fake.last_generate_call["confirm"] is True
    assert "Geração enviada: 0 créditos (projeto proj-123). Acompanhe com `flow media list --project proj-123`." in result.output


def test_generate_video_dry_run_text():
    fake = GenerateFakeBackend(cost=24, project_id="proj-456")
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["generate", "video", "mar revolto", "--duration", "6", "--resolution", "720p", "--aspect", "9:16", "--count", "2"],
        obj={"backend": fake},
    )
    assert result.exit_code == 0
    assert fake.last_generate_call["confirm"] is False
    assert fake.last_generate_call["duration"] == "6s"
    assert fake.last_generate_call["resolution"] == "720p"
    assert fake.last_generate_call["aspect"] == "9:16"
    assert fake.last_generate_call["count"] == 2
    assert "Dry-run: esta geração usaria 24 créditos (projeto proj-456). Nada foi gerado. Use --yes para gerar." in result.output


def test_generate_video_confirmed_json():
    fake = GenerateFakeBackend(cost=24, project_id="proj-456")
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--json", "generate", "video", "mar revolto", "--yes"],
        obj={"backend": fake},
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["submitted"] is True
    assert data["dry_run"] is False
    assert data["cost"] == 24
    assert data["kind"] == "video"


def test_generate_empty_prompt_fails():
    fake = GenerateFakeBackend()
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "image", "   "], obj={"backend": fake})
    assert result.exit_code != 0
    assert "prompt" in result.output.lower()


def test_generate_backend_error_fails():
    fake = GenerateFakeBackend(should_fail=True)
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "image", "teste"], obj={"backend": fake})
    assert result.exit_code == 1
    assert "Falha na geração" in result.output


# --- Testes de Defesa em Profundidade e MockPage ---

class MockLocator:
    def __init__(self, role, name=None, exact=False, text_content="", should_fail_click=False):
        self.role = role
        self.name = name
        self.exact = exact
        self._text = text_content
        self.should_fail_click = should_fail_click
        self.clicks = []
        self.fills = []
        self.presses = []

    def click(self, force=False, timeout=None):
        if self.should_fail_click:
            raise Exception("Timeout click error")
        self.clicks.append({"force": force, "timeout": timeout})

    def fill(self, text, timeout=None):
        self.fills.append(text)

    def press(self, key):
        self.presses.append(key)

    def inner_text(self, timeout=None):
        return self._text

    @property
    def last(self):
        return self

    @property
    def first(self):
        return self


class MockPage:
    def __init__(self, cost_text="A geração vai usar 15 créditos"):
        self.locators: dict[tuple, MockLocator] = {}
        self.cost_text = cost_text
        self.goto_calls = []
        self.keyboard_presses = []

        class Keyboard:
            def __init__(outer):
                outer.keyboard_presses = []
            def press(k_self, key):
                self.keyboard_presses.append(key)

        self.keyboard = Keyboard()

    def get_by_role(self, role, name=None, exact=False):
        key = (role, name, exact)
        if key not in self.locators:
            # Texto especial para gatilho e custo
            text = ""
            if name == "Gatilho de configurações":
                text = "Config"
            self.locators[key] = MockLocator(role, name, exact, text_content=text)
        return self.locators[key]

    def locator(self, selector):
        key = ("selector", selector, False)
        if key not in self.locators:
            # Simula o overlay de custo ou modelos
            self.locators[key] = MockLocator("selector", selector, False, text_content=self.cost_text)
        return self.locators[key]

    def wait_for_load_state(self, state=None, timeout=None):
        pass


def test_submit_generation_raises_if_not_confirmed():
    mock_page = MockPage()
    pb = PlaywrightBackend(profile_path=MagicMock())

    with pytest.raises(FlowError, match="Confirmação necessária"):
        pb._submit_generation(mock_page, confirm=False)

    btn = mock_page.get_by_role("button", name="Iniciar geração")
    assert len(btn.clicks) == 0
    assert "Enter" not in mock_page.keyboard_presses


def test_submit_generation_clicks_once_when_confirmed():
    mock_page = MockPage()
    pb = PlaywrightBackend(profile_path=MagicMock())

    pb._submit_generation(mock_page, confirm=True)

    btn = mock_page.get_by_role("button", name="Iniciar geração")
    assert len(btn.clicks) == 1


def test_playwright_backend_generate_dry_run_never_submits(monkeypatch):
    mock_page = MockPage(cost_text="A geração vai usar 24 créditos")
    pb = PlaywrightBackend(profile_path=MagicMock())

    monkeypatch.setattr(pb, "_ensure_browser", lambda headless=None: mock_page)
    monkeypatch.setattr(pb, "list_projects", lambda: [{"id": "p-test", "url": "https://flow.google.com/project/p-test"}])
    monkeypatch.setattr(pb, "_goto", lambda page, url: None)

    res = pb.generate(
        "image",
        "um lindo por do sol",
        aspect="16:9",
        count=1,
        confirm=False,
    )

    assert res["dry_run"] is True
    assert res["submitted"] is False
    assert res["cost"] == 24
    assert res["project"] == "p-test"

    # Verificação de segurança estrita:
    submit_btn = mock_page.get_by_role("button", name="Iniciar geração")
    assert len(submit_btn.clicks) == 0
    assert "Enter" not in mock_page.keyboard_presses

    # Caixa de texto limpa ao final do dry-run
    prompt_box = mock_page.get_by_role("textbox", name="O que você quer criar?")
    assert prompt_box.fills[-1] == ""  # limpo no final


def test_playwright_backend_generate_confirmed_submits(monkeypatch):
    mock_page = MockPage(cost_text="A geração vai usar 10 créditos")
    pb = PlaywrightBackend(profile_path=MagicMock())

    monkeypatch.setattr(pb, "_ensure_browser", lambda headless=None: mock_page)
    monkeypatch.setattr(pb, "list_projects", lambda: [{"id": "p-test", "url": "https://flow.google.com/project/p-test"}])
    monkeypatch.setattr(pb, "_goto", lambda page, url: None)

    res = pb.generate(
        "video",
        "um rio calmo",
        aspect="16:9",
        count=1,
        resolution="720p",
        duration="4s",
        confirm=True,
    )

    assert res["dry_run"] is False
    assert res["submitted"] is True
    assert res["cost"] == 10

class MultiReadMockLocator:
    def __init__(self, texts: list[str]):
        self.texts = texts
        self.index = 0

    def inner_text(self, timeout=None):
        if not self.texts:
            return ""
        val = self.texts[min(self.index, len(self.texts) - 1)]
        self.index += 1
        return val

    @property
    def first(self):
        return self

    @property
    def last(self):
        return self


class DynamicMockPage(MockPage):
    def __init__(self, settings_texts: list[str]):
        super().__init__()
        self.settings_locator = MultiReadMockLocator(settings_texts)

    def locator(self, selector):
        if selector == "flow-prompt-box-settings":
            return self.settings_locator
        return super().locator(selector)


def test_playwright_backend_generate_reads_stable_new_cost(monkeypatch):
    # Primeiro read devolve valor antigo (30), seguintes devolvem valor novo (10)
    mock_page = DynamicMockPage([
        "A geração vai usar 30 créditos",
        "A geração vai usar 10 créditos",
        "A geração vai usar 10 créditos",
    ])
    pb = PlaywrightBackend(profile_path=MagicMock())

    monkeypatch.setattr(pb, "_ensure_browser", lambda headless=None: mock_page)
    monkeypatch.setattr(pb, "list_projects", lambda: [{"id": "p-test", "url": "https://flow.google.com/project/p-test"}])
    monkeypatch.setattr(pb, "_goto", lambda page, url: None)

    sleep_calls = []
    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    res = pb.generate(
        "image",
        "um gato rajado",
        count=1,
        confirm=False,
    )

    # O resultado deve ser o valor novo estabilizado (10 créditos), não o valor antigo (30)
    assert res["cost"] == 10
    # Verifica que após último clique de opção esperou 1.5s
    assert 1.5 in sleep_calls
    # Verifica que entre leituras esperou 0.7s
    assert 0.7 in sleep_calls


def test_read_generation_cost_falls_back_to_last_if_not_stabilized(monkeypatch):
    # Se não estabilizar em 2 leituras iguais consecutivas, usa a última
    mock_page = DynamicMockPage([
        "A geração vai usar 10 créditos",
        "A geração vai usar 20 créditos",
        "A geração vai usar 30 créditos",
        "A geração vai usar 40 créditos",
        "A geração vai usar 50 créditos",
        "A geração vai usar 60 créditos",
    ])
    pb = PlaywrightBackend(profile_path=MagicMock())
    monkeypatch.setattr("time.sleep", lambda s: None)

    cost = pb._read_generation_cost(mock_page)
    assert cost == 60


def test_read_generation_cost_fallback_to_overlay_and_body(monkeypatch):
    # Testa fallback quando flow-prompt-box-settings não tem texto de crédito
    class FallbackMockPage:
        def __init__(self):
            self.settings_locator = MockLocator("selector", "flow-prompt-box-settings", text_content="")
            self.overlay_locator = MockLocator("selector", ".cdk-overlay-pane", text_content="A geração vai usar 45 créditos")
            self.body_locator = MockLocator("selector", "body", text_content="")

        def locator(self, selector):
            if selector == "flow-prompt-box-settings":
                return self.settings_locator
            if selector == ".cdk-overlay-pane":
                return self.overlay_locator
            return self.body_locator

    mock_page = FallbackMockPage()
    pb = PlaywrightBackend(profile_path=MagicMock())
    monkeypatch.setattr("time.sleep", lambda s: None)

    cost = pb._read_generation_cost(mock_page)
    assert cost == 45


def test_playwright_backend_generate_video_resolution_unavailable_ignored(monkeypatch):
    mock_page = MockPage(cost_text="A geração vai usar 15 créditos")
    # Mock locator para resolução 720p que falha no click com exceção
    res_locator = MockLocator("radio", name="720p", exact=True, should_fail_click=True)
    mock_page.locators[("radio", "720p", True)] = res_locator

    pb = PlaywrightBackend(profile_path=MagicMock())
    monkeypatch.setattr(pb, "_ensure_browser", lambda headless=None: mock_page)
    monkeypatch.setattr(pb, "list_projects", lambda: [{"id": "p-test", "url": "https://flow.google.com/project/p-test"}])
    monkeypatch.setattr(pb, "_goto", lambda page, url: None)
    monkeypatch.setattr("time.sleep", lambda s: None)

    res = pb.generate(
        "video",
        "video sem radio 720p",
        resolution="720p",
        duration="4s",
        confirm=False,
    )

    assert res["cost"] == 15
    assert res["kind"] == "video"
    assert res["resolution"] == "720p"
    assert res["duration"] == "4s"
    assert res["dry_run"] is True
    # Duração ainda clicada normalmente com force=True e timeout=3000
    dur_locator = mock_page.get_by_role("radio", name="4s", exact=True)
    assert len(dur_locator.clicks) == 1
    assert dur_locator.clicks[0]["force"] is True
    assert dur_locator.clicks[0]["timeout"] == 3000



