import pytest
from flow_cli.browser_utils import (
    FlowError,
    wait_for_selector,
    click_by_text,
    safe_text,
)


class FakeElement:
    def __init__(self, text: str = ""):
        self._text = text

    def inner_text(self) -> str:
        return self._text

    def click(self) -> None:
        pass


class FakePage:
    def __init__(self, elements=None, should_fail_wait=False):
        self.elements = elements or {}
        self.should_fail_wait = should_fail_wait
        self.clicked_text = []

    def wait_for_selector(self, selector: str, timeout: int = 30000):
        if self.should_fail_wait or selector not in self.elements:
            raise Exception("Timeout esperando elemento")
        return self.elements[selector]

    def query_selector(self, selector: str):
        return self.elements.get(selector)

    def get_by_text(self, text: str, exact: bool = False):
        class Locator:
            def __init__(self, parent, t):
                self.parent = parent
                self.t = t

            def click(self, timeout: int = 30000):
                self.parent.clicked_text.append(self.t)

        return Locator(self, text)


def test_wait_for_selector_success():
    elem = FakeElement("conteudo")
    page = FakePage(elements={"#test": elem})
    result = wait_for_selector(page, "#test", timeout_ms=500)
    assert result == elem


def test_wait_for_selector_failure():
    page = FakePage(should_fail_wait=True)
    with pytest.raises(FlowError) as exc_info:
        wait_for_selector(page, "#missing", timeout_ms=100)
    assert "Elemento não encontrado" in str(exc_info.value) or "#missing" in str(exc_info.value)


def test_click_by_text_success():
    page = FakePage()
    click_by_text(page, "Entrar")
    assert "Entrar" in page.clicked_text


def test_click_by_text_failure():
    class BrokenPage:
        def get_by_text(self, text: str, exact: bool = False):
            raise Exception("Clique falhou")

    page = BrokenPage()
    with pytest.raises(FlowError) as exc_info:
        click_by_text(page, "Botão")
    assert "Falha ao clicar" in str(exc_info.value) or "Botão" in str(exc_info.value)


def test_safe_text_existing():
    elem = FakeElement("Texto Aqui")
    page = FakePage(elements={".status": elem})
    text = safe_text(page, ".status")
    assert text == "Texto Aqui"


def test_safe_text_missing():
    page = FakePage(elements={})
    assert safe_text(page, ".inexistente") == ""
