"""Exceções e utilitários para automação de navegador com Playwright."""
from typing import Any


class FlowError(Exception):
    """Exceção base para erros de operação e automação do Flow."""
    pass


def wait_for_selector(page: Any, selector: str, timeout_ms: int = 10000) -> Any:
    """Aguarda um seletor na página com mensagem de erro clara."""
    try:
        return page.wait_for_selector(selector, timeout=timeout_ms)
    except Exception as exc:
        raise FlowError(f"Elemento não encontrado no tempo limite ({timeout_ms}ms): {selector}") from exc


def click_by_text(page: Any, text: str, exact: bool = False, timeout_ms: int = 5000) -> None:
    """Clica em elemento pelo texto visível."""
    try:
        locator = page.get_by_text(text, exact=exact)
        locator.click(timeout=timeout_ms)
    except Exception as exc:
        raise FlowError(f"Falha ao clicar no texto '{text}': {exc}") from exc


def safe_text(page: Any, selector: str) -> str:
    """Retorna texto do seletor ou string vazia se ausente."""
    try:
        element = page.query_selector(selector)
        if element:
            return element.inner_text().strip()
    except Exception:
        pass
    return ""
