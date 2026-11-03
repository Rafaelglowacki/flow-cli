"""Backends de automação e comunicação com o Flow."""
from abc import ABC, abstractmethod
from pathlib import Path
import shutil
import time
from typing import Any
from flow_cli.browser_utils import FlowError

BASE_URL = "https://flow.google.com/"


class Backend(ABC):
    """Interface abstrata para o backend de automação do Flow."""

    @abstractmethod
    def is_logged_in(self) -> bool:
        """Verifica se há sessão autenticada ativa."""
        pass

    @abstractmethod
    def open_login(self) -> None:
        """Abre navegador visível para login manual do usuário."""
        pass

    @abstractmethod
    def logout(self) -> None:
        """Limpa sessão/perfil armazenado."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Fecha navegador e recursos associados."""
        pass


class PlaywrightBackend(Backend):
    """Backend baseado em Playwright com perfil de navegador persistente."""

    def __init__(self, profile_path: Path, headless: bool = True):
        self.profile_path = profile_path
        self.headless = headless
        self._playwright = None
        self._context = None
        self._page = None

    def _ensure_browser(self, headless: bool | None = None) -> Any:
        """Inicializa Playwright e contexto persistente de forma preguiçosa."""
        if self._context is not None:
            return self._page

        from playwright.sync_api import sync_playwright

        is_headless = self.headless if headless is None else headless
        self.profile_path.mkdir(parents=True, exist_ok=True)

        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_path),
            headless=is_headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = self._context.new_page()

        return self._page

    def is_logged_in(self) -> bool:
        """Verifica login acessando a URL base no modo headless."""
        try:
            page = self._ensure_browser(headless=True)
            page.goto(BASE_URL, wait_until="networkidle", timeout=20000)

            # Redirecionado para tela de login do Google
            if "accounts.google.com" in page.url:
                return False

            # Presença explícita de botão de entrar / sign in
            sign_in_btn = page.query_selector(
                'button:has-text("Sign in"), button:has-text("Fazer login"), button:has-text("Entrar")'
            )
            if sign_in_btn is not None:
                return False

            # Se permaneceu em flow.google.com sem prompt de login
            if "flow.google.com" in page.url and "accounts.google.com" not in page.url:
                return True

            return False
        except Exception:
            return False

    def open_login(self) -> None:
        """Abre navegador visível para a pessoa entrar manualmente no Flow."""
        # Se havia contexto headless aberto, fecha antes de abrir visível
        self.close()

        page = self._ensure_browser(headless=False)
        page.goto(BASE_URL)

        # Aguarda a pessoa fazer login
        # Verifica periodicamente se já está logada e em flow.google.com
        start_time = time.time()
        timeout_seconds = 300  # 5 minutos para login manual

        while time.time() - start_time < timeout_seconds:
            try:
                current_url = page.url
                if "accounts.google.com" not in current_url and "flow.google.com" in current_url:
                    sign_in_btn = page.query_selector(
                        'button:has-text("Sign in"), button:has-text("Fazer login"), button:has-text("Entrar")'
                    )
                    if sign_in_btn is None:
                        # Login concluído
                        return
            except Exception:
                # Caso a janela tenha sido fechada prematuramente pelo usuário
                break
            time.sleep(1)

        raise FlowError("Tempo limite esgotado para login manual ou janela fechada.")

    def logout(self) -> None:
        """Fecha navegador e remove diretório de perfil persistente."""
        self.close()
        if self.profile_path.exists():
            shutil.rmtree(self.profile_path, ignore_errors=True)

    def close(self) -> None:
        """Encerra contexto e processo do Playwright."""
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        finally:
            self._context = None
            self._page = None

        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        finally:
            self._playwright = None
