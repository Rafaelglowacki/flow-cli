import json
import pytest
from click.testing import CliRunner
from flow_cli.cli import main
from flow_cli.backend import Backend
from flow_cli.browser_utils import FlowError


class ReadFakeBackend(Backend):
    def __init__(
        self,
        projects=None,
        models=None,
        credits_data=None,
        media_items=None,
        should_fail=False,
    ):
        self._projects = projects if projects is not None else [
            {"id": "p-1", "title": "Projeto Alfa", "url": "https://flow.google.com/project/p-1", "updated": "nov. 03 - 10:00"},
            {"id": "p-2", "title": "Projeto Beta", "url": "https://flow.google.com/project/p-2", "updated": "nov. 02 - 18:30"},
        ]
        self._models = models if models is not None else [
            {"kind": "image", "name": "Nano Banana 2.1", "source": "live"},
            {"kind": "video", "name": "Omni 1.1 Flash", "source": "live"},
        ]
        self._credits_data = credits_data if credits_data is not None else {
            "credits": 1050,
            "reset": "20 de nov., 20:08",
        }
        self._media_items = media_items if media_items is not None else [
            {"id": "m-1", "project": "p-1", "kind": "image", "name": "Foto 1", "thumbnail": "https://flow.google.com/asb/1"},
            {"id": "m-2", "project": "p-1", "kind": "video", "name": "Video 1", "thumbnail": "https://flow.google.com/asb/2"},
            {"id": "m-3", "project": "p-2", "kind": "image", "name": "Foto 2", "thumbnail": "https://flow.google.com/asb/3"},
        ]
        self.should_fail = should_fail
        self.closed = False

    def is_logged_in(self) -> bool:
        return True

    def open_login(self) -> None:
        pass

    def logout(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    def list_projects(self):
        if self.should_fail:
            raise FlowError("falha ao listar projetos")
        return self._projects

    def list_models(self, kind=None):
        if self.should_fail:
            raise FlowError("falha ao listar modelos")
        if kind:
            return [m for m in self._models if m["kind"] == kind]
        return self._models

    def get_credits(self):
        if self.should_fail:
            raise FlowError("falha ao obter créditos")
        return self._credits_data

    def list_media(self, project_id=None, kind=None):
        if self.should_fail:
            raise FlowError("falha ao listar mídias")
        items = self._media_items
        if project_id:
            items = [m for m in items if m["project"] == project_id]
        if kind:
            items = [m for m in items if m["kind"] == kind]
        return items


def test_projects_list_table():
    fake = ReadFakeBackend()
    runner = CliRunner()
    result = runner.invoke(main, ["projects", "list"], obj={"backend": fake})
    assert result.exit_code == 0
    assert fake.closed is True
    assert "p-1" in result.output
    assert "Projeto Alfa" in result.output
    # Coluna updated não deve estar na tabela
    assert "nov. 03 - 10:00" not in result.output
    assert "updated" not in result.output.lower()


def test_projects_list_json():
    fake = ReadFakeBackend()
    runner = CliRunner()
    result = runner.invoke(main, ["--json", "projects", "list"], obj={"backend": fake})
    assert result.exit_code == 0
    assert fake.closed is True
    data = json.loads(result.output)
    assert len(data) == 2
    assert data[0]["id"] == "p-1"
    assert data[0]["updated"] == "nov. 03 - 10:00"


def test_projects_list_error():
    fake = ReadFakeBackend(should_fail=True)
    runner = CliRunner()
    result = runner.invoke(main, ["projects", "list"], obj={"backend": fake})
    assert result.exit_code == 1
    assert "falha ao listar projetos" in result.output


def test_models_list_table_all_and_filtered():
    fake = ReadFakeBackend()
    runner = CliRunner()
    
    # Todos
    res_all = runner.invoke(main, ["models", "list"], obj={"backend": fake})
    assert res_all.exit_code == 0
    assert "Nano Banana 2.1" in res_all.output
    assert "Omni 1.1 Flash" in res_all.output

    # Filtro kind=image
    res_img = runner.invoke(main, ["models", "list", "--kind", "image"], obj={"backend": fake})
    assert res_img.exit_code == 0
    assert "Nano Banana 2.1" in res_img.output
    assert "Omni 1.1 Flash" not in res_img.output

    # Filtro kind=video
    res_vid = runner.invoke(main, ["models", "list", "--kind", "video"], obj={"backend": fake})
    assert res_vid.exit_code == 0
    assert "Omni 1.1 Flash" in res_vid.output
    assert "Nano Banana 2.1" not in res_vid.output


def test_models_list_json():
    fake = ReadFakeBackend()
    runner = CliRunner()
    result = runner.invoke(main, ["--json", "models", "list", "--kind", "image"], obj={"backend": fake})
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["kind"] == "image"
    assert data[0]["source"] == "live"


def test_models_list_error():
    fake = ReadFakeBackend(should_fail=True)
    runner = CliRunner()
    result = runner.invoke(main, ["models", "list"], obj={"backend": fake})
    assert result.exit_code == 1
    assert "falha ao listar modelos" in result.output


def test_credits_output_and_json():
    fake = ReadFakeBackend()
    runner = CliRunner()

    res = runner.invoke(main, ["credits"], obj={"backend": fake})
    assert res.exit_code == 0
    assert "Créditos: 1050" in res.output
    assert "Redefinição do limite de uso: 20 de nov., 20:08" in res.output or "20 de nov., 20:08" in res.output

    res_json = runner.invoke(main, ["--json", "credits"], obj={"backend": fake})
    assert res_json.exit_code == 0
    data = json.loads(res_json.output)
    assert data["credits"] == 1050
    assert data["reset"] == "20 de nov., 20:08"


def test_credits_no_reset():
    fake = ReadFakeBackend(credits_data={"credits": 50, "reset": None})
    runner = CliRunner()
    res = runner.invoke(main, ["credits"], obj={"backend": fake})
    assert res.exit_code == 0
    assert "Créditos: 50" in res.output
    assert "Redefinição" not in res.output


def test_credits_error():
    fake = ReadFakeBackend(should_fail=True)
    runner = CliRunner()
    result = runner.invoke(main, ["credits"], obj={"backend": fake})
    assert result.exit_code == 1
    assert "falha ao obter créditos" in result.output


def test_media_list_table_and_filters():
    fake = ReadFakeBackend()
    runner = CliRunner()

    # Todas
    res = runner.invoke(main, ["media", "list"], obj={"backend": fake})
    assert res.exit_code == 0
    assert "m-1" in res.output
    assert "m-2" in res.output
    assert "m-3" in res.output

    # Por projeto
    res_proj = runner.invoke(main, ["media", "list", "--project", "p-1"], obj={"backend": fake})
    assert res_proj.exit_code == 0
    assert "m-1" in res_proj.output
    assert "m-2" in res_proj.output
    assert "m-3" not in res_proj.output

    # Por kind
    res_vid = runner.invoke(main, ["media", "list", "--kind", "video"], obj={"backend": fake})
    assert res_vid.exit_code == 0
    assert "m-2" in res_vid.output
    assert "m-1" not in res_vid.output
    assert "m-3" not in res_vid.output


def test_media_list_json():
    fake = ReadFakeBackend()
    runner = CliRunner()
    res = runner.invoke(main, ["--json", "media", "list", "--project", "p-2"], obj={"backend": fake})
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert len(data) == 1
    assert data[0]["id"] == "m-3"


def test_media_list_error():
    fake = ReadFakeBackend(should_fail=True)
    runner = CliRunner()
    res = runner.invoke(main, ["media", "list"], obj={"backend": fake})
    assert res.exit_code == 1
    assert "falha ao listar mídias" in res.output


def test_backend_base_unsupported_methods():
    class MinimalBackend(Backend):
        def is_logged_in(self) -> bool:
            return True
        def open_login(self) -> None:
            pass
        def logout(self) -> None:
            pass
        def close(self) -> None:
            pass

    base = MinimalBackend()
    with pytest.raises(FlowError, match="não suportado por este backend"):
        base.list_projects()
    with pytest.raises(FlowError, match="não suportado por este backend"):
        base.list_models()
    with pytest.raises(FlowError, match="não suportado por este backend"):
        base.get_credits()
    with pytest.raises(FlowError, match="não suportado por este backend"):
        base.list_media()


def test_playwright_backend_list_projects_logic(monkeypatch, tmp_path):
    from flow_cli.backend import PlaywrightBackend

    backend = PlaywrightBackend(profile_path=tmp_path)
    eval_calls = []

    class MockPage:
        url = "https://flow.google.com/"

        def goto(self, url, **kwargs):
            pass

        def wait_for_selector(self, selector, **kwargs):
            pass

        def eval_on_selector_all(self, selector, script):
            eval_calls.append((selector, script))
            return [
                {"href": "/project/1111-2222", "title": " nov. 03 - 15:49 "},
                {"href": "/project/3333-4444", "title": "Meu Projeto"},
                {"href": "/project/5555-6666", "title": "   "},
            ]

    monkeypatch.setattr(backend, "_ensure_browser", lambda headless=True: MockPage())

    projs = backend.list_projects()
    assert len(projs) == 3

    assert eval_calls[0][0] == "flow-project-card"
    assert "project-title-text" in eval_calls[0][1]
    assert "project-thumbnail-container" in eval_calls[0][1]

    assert projs[0]["id"] == "1111-2222"
    assert projs[0]["title"] == "nov. 03 - 15:49"
    assert projs[0]["updated"] == "nov. 03 - 15:49"

    assert projs[1]["id"] == "3333-4444"
    assert projs[1]["title"] == "Meu Projeto"
    assert projs[1]["updated"] == ""

    assert projs[2]["id"] == "5555-6666"
    assert projs[2]["title"] == "Sem título"
    assert projs[2]["updated"] == ""


def test_playwright_backend_get_credits_multiline(monkeypatch, tmp_path):
    from flow_cli.backend import PlaywrightBackend

    backend = PlaywrightBackend(profile_path=tmp_path)

    class MockDialog:
        def wait_for(self, **kwargs):
            pass

        def inner_text(self):
            return (
                "Configurações da conta\n"
                "1.050 créditos do Google Flow\n"
                "Redefinição do limite de uso: 20 de nov., 20:08\n"
                "Sair de todas as contas\n"
                "frame_spark\n"
                "Marca-d'água visível\n"
                "Privacidade."
            )

    class MockKeyboard:
        def press(self, key):
            pass

    class MockPage:
        url = "https://flow.google.com/"
        keyboard = MockKeyboard()

        def goto(self, url, **kwargs):
            pass

        def get_by_role(self, role, name=None):
            if role == "dialog":
                return MockDialog()

            class MockButton:
                def click(self, **kwargs):
                    pass

            return MockButton()

    monkeypatch.setattr(backend, "_ensure_browser", lambda headless=True: MockPage())

    credits_info = backend.get_credits()
    assert credits_info["credits"] == 1050
    assert credits_info["reset"] == "20 de nov., 20:08"


def test_playwright_backend_list_media_logic(monkeypatch, tmp_path):
    from flow_cli.backend import PlaywrightBackend

    backend = PlaywrightBackend(profile_path=tmp_path)
    eval_calls = []

    class MockPage:
        url = "https://flow.google.com/project/p-1"

        def goto(self, url, **kwargs):
            pass

        def eval_on_selector_all(self, selector, script):
            eval_calls.append((selector, script))
            return [
                {
                    "id": "m-1",
                    "thumbnail": "https://flow.google.com/asb/1",
                    "name": "Flexicon0523_pindown.io_1793545580.jpg",
                    "has_video": False,
                },
                {
                    "id": "m-2",
                    "thumbnail": "https://flow.google.com/asb/2",
                    "name": "Alt description",
                    "has_video": True,
                },
                {
                    "id": "m-3",
                    "thumbnail": "https://flow.google.com/asb/3",
                    "name": "Sem título",
                    "has_video": False,
                },
            ]

    monkeypatch.setattr(backend, "_ensure_browser", lambda headless=True: MockPage())
    monkeypatch.setattr(backend, "list_projects", lambda: [{"id": "p-1"}])

    media_items = backend.list_media(project_id="p-1")
    assert len(media_items) == 3
    assert eval_calls[0][0] == "img[data-media-id]"
    assert "closest" in eval_calls[0][1]
    assert "[role=group]" in eval_calls[0][1] or '[role=\\"group\\"]' in eval_calls[0][1] or "[role='group']" in eval_calls[0][1]

    assert media_items[0]["name"] == "Flexicon0523_pindown.io_1793545580.jpg"
    assert media_items[0]["kind"] == "image"

    assert media_items[1]["name"] == "Alt description"
    assert media_items[1]["kind"] == "video"

    assert media_items[2]["name"] == "Sem título"
    assert media_items[2]["kind"] == "image"


def test_playwright_backend_goto_helper(monkeypatch, tmp_path):
    from flow_cli.backend import PlaywrightBackend

    backend = PlaywrightBackend(profile_path=tmp_path)
    monkeypatch.setattr("time.sleep", lambda s: None)

    calls = []

    class MockPage:
        def goto(self, url, **kwargs):
            calls.append(("goto", url, kwargs))

        def wait_for_load_state(self, state, **kwargs):
            calls.append(("wait_for_load_state", state, kwargs))

    page = MockPage()
    backend._goto(page, "https://flow.google.com/test")

    assert calls == [
        ("goto", "https://flow.google.com/test", {"wait_until": "domcontentloaded", "timeout": 45000}),
        ("wait_for_load_state", "networkidle", {"timeout": 10000}),
    ]


def test_playwright_backend_goto_helper_ignores_timeout(monkeypatch, tmp_path):
    from flow_cli.backend import PlaywrightBackend

    backend = PlaywrightBackend(profile_path=tmp_path)
    monkeypatch.setattr("time.sleep", lambda s: None)

    class MockPage:
        def goto(self, url, **kwargs):
            pass

        def wait_for_load_state(self, state, **kwargs):
            raise TimeoutError("timeout networkidle")

    page = MockPage()
    # Não deve levantar exceção
    backend._goto(page, "https://flow.google.com/test")


def test_playwright_backend_list_models_live(monkeypatch, tmp_path):
    from flow_cli.backend import PlaywrightBackend

    backend = PlaywrightBackend(profile_path=tmp_path)
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr(backend, "list_projects", lambda: [{"id": "p-1", "url": "https://flow.google.com/project/p-1"}])

    actions = []

    class MockLocator:
        def __init__(self, name, text=""):
            self.name = name
            self.text = text

        @property
        def last(self):
            return self

        def inner_text(self):
            return self.text

    class MockRadio:
        def __init__(self, label):
            self.label = label

        def click(self, force=False):
            actions.append(f"radio_click_{self.label}_force_{force}")

    class MockButton:
        def __init__(self, name):
            self.name = name

        @property
        def first(self):
            return self

        def click(self, **kwargs):
            actions.append(f"button_click_{self.name}")

    class MockKeyboard:
        def press(self, key):
            actions.append(f"key_press_{key}")

    current_radio = ["Imagem"]

    class MockPage:
        url = "https://flow.google.com/project/p-1"
        keyboard = MockKeyboard()

        def goto(self, url, **kwargs):
            actions.append(f"goto_{url}")

        def wait_for_load_state(self, state, **kwargs):
            pass

        def get_by_role(self, role, name=None):
            if role == "radio":
                current_radio[0] = name
                return MockRadio(name)
            if role == "button":
                return MockButton(name)
            raise ValueError(f"role desconhecido: {role}")

        def locator(self, selector):
            if selector == ".cdk-overlay-pane":
                if current_radio[0] == "Imagem":
                    return MockLocator(
                        selector,
                        "volume_up\n🍌 Nano Banana Pro\n🍌 Nano Banana 2 Lite\n🍌 Nano Banana 2.1"
                    )
                else:
                    return MockLocator(
                        selector,
                        "Omni 1.1 Flash\nvolume_up\nVeo 3.1 - Lite\nVeo 3.1 - Fast\nVeo 3.1 - Quality"
                    )
            if selector == "body":
                return MockLocator(selector, "")
            return MockLocator(selector, "")

    mock_page = MockPage()
    monkeypatch.setattr(backend, "_ensure_browser", lambda headless=True: mock_page)

    models = backend.list_models()
    assert len(models) == 7
    img_models = [m for m in models if m["kind"] == "image"]
    vid_models = [m for m in models if m["kind"] == "video"]
    assert [m["name"] for m in img_models] == ["Nano Banana Pro", "Nano Banana 2 Lite", "Nano Banana 2.1"]
    assert all(m["source"] == "live" for m in img_models)
    assert [m["name"] for m in vid_models] == ["Omni 1.1 Flash", "Veo 3.1 - Lite", "Veo 3.1 - Fast", "Veo 3.1 - Quality"]
    assert all(m["source"] == "live" for m in vid_models)

    # Verifica restauração do radio Imagem no final
    assert "radio_click_Imagem_force_True" in actions[-3:]


def test_playwright_backend_list_models_partial_fallback(monkeypatch, tmp_path):
    from flow_cli.backend import PlaywrightBackend

    backend = PlaywrightBackend(profile_path=tmp_path)
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr(backend, "list_projects", lambda: [{"id": "p-1", "url": "https://flow.google.com/project/p-1"}])

    current_radio = ["Imagem"]

    class MockLocator:
        def __init__(self, text=""):
            self.text = text

        @property
        def last(self):
            return self

        def inner_text(self):
            return self.text

    class MockRadio:
        def click(self, force=False):
            pass

    class MockButton:
        @property
        def first(self):
            return self

        def click(self, **kwargs):
            pass

    class MockKeyboard:
        def press(self, key):
            pass

    class MockPage:
        url = "https://flow.google.com/project/p-1"
        keyboard = MockKeyboard()

        def goto(self, url, **kwargs):
            pass

        def wait_for_load_state(self, state, **kwargs):
            pass

        def get_by_role(self, role, name=None):
            if role == "radio":
                current_radio[0] = name
                return MockRadio()
            if role == "button":
                return MockButton()
            raise ValueError(f"role desconhecido: {role}")

        def locator(self, selector):
            # Imagem retorna vazio -> fallback static
            # Vídeo retorna live
            if selector == ".cdk-overlay-pane":
                if current_radio[0] == "Imagem":
                    return MockLocator("")
                else:
                    return MockLocator("Omni 1.1 Flash\nVeo 3.1 - Lite")
            return MockLocator("")

    mock_page = MockPage()
    monkeypatch.setattr(backend, "_ensure_browser", lambda headless=True: mock_page)

    models = backend.list_models()
    img_models = [m for m in models if m["kind"] == "image"]
    vid_models = [m for m in models if m["kind"] == "video"]

    # Imagem deve ser static
    assert all(m["source"] == "static" for m in img_models)
    assert len(img_models) == 3

    # Vídeo deve ser live
    assert all(m["source"] == "live" for m in vid_models)
    assert [m["name"] for m in vid_models] == ["Omni 1.1 Flash", "Veo 3.1 - Lite"]


