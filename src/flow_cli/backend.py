"""Backends de automação e comunicação com o Flow."""
from abc import ABC, abstractmethod
from pathlib import Path
import shutil
import time
from typing import Any
from flow_cli.browser_utils import FlowError
from flow_cli.parsers import (
    parse_credits,
    project_id_from_href,
    parse_reset,
    classify_media,
    is_standard_date,
    parse_model_names,
)

BASE_URL = "https://flow.google.com/"

STATIC_MODELS = [
    {"kind": "image", "name": "Nano Banana Pro", "source": "static"},
    {"kind": "image", "name": "Nano Banana 2 Lite", "source": "static"},
    {"kind": "image", "name": "Nano Banana 2.1", "source": "static"},
    {"kind": "video", "name": "Omni 1.1 Flash", "source": "static"},
    {"kind": "video", "name": "Veo 3.1 - Lite", "source": "static"},
    {"kind": "video", "name": "Veo 3.1 - Fast", "source": "static"},
    {"kind": "video", "name": "Veo 3.1 - Quality", "source": "static"},
]


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

    def list_projects(self) -> list[dict]:
        """Lista projetos existentes na conta."""
        raise FlowError("não suportado por este backend")

    def list_models(self, kind: str | None = None) -> list[dict]:
        """Lista modelos suportados para geração."""
        raise FlowError("não suportado por este backend")

    def get_credits(self) -> dict:
        """Consulta créditos e data de redefinição."""
        raise FlowError("não suportado por este backend")

    def list_media(self, project_id: str | None = None, kind: str | None = None) -> list[dict]:
        """Lista mídias de projetos."""
        raise FlowError("não suportado por este backend")


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

    def _goto(self, page: Any, url: str) -> None:
        """Navega de forma robusta evitando timeouts com networkidle."""
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        time.sleep(2)

    def is_logged_in(self) -> bool:
        """Verifica login acessando a URL base no modo headless."""
        try:
            page = self._ensure_browser(headless=True)
            self._goto(page, BASE_URL)

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

    def list_projects(self) -> list[dict]:
        """Lista projetos existentes na conta usando seletores da home."""
        page = self._ensure_browser(headless=self.headless)
        try:
            self._goto(page, BASE_URL)
            if "accounts.google.com" in page.url:
                raise FlowError("Sessão não autenticada. Execute 'flow auth login'.")

            try:
                page.wait_for_selector("flow-project-card", timeout=10000)
            except Exception:
                pass

            cards_data = page.eval_on_selector_all(
                "flow-project-card",
                """cards => cards.map(c => {
                    const link = c.querySelector('a.project-thumbnail-container[href^="/project/"]') || c.querySelector('a[href^="/project/"]');
                    const span = c.querySelector('span.project-title-text');
                    return {
                        href: link ? link.getAttribute('href') : '',
                        title: span ? (span.innerText || span.textContent || '').trim() : ''
                    };
                })"""
            )

            projects = []
            seen_ids = set()
            for card in cards_data:
                href = card.get("href") or ""
                p_id = project_id_from_href(href)
                if not p_id or p_id in seen_ids:
                    continue
                seen_ids.add(p_id)

                full_url = f"https://flow.google.com/project/{p_id}"
                raw_title = (card.get("title") or "").strip()
                title = raw_title if raw_title else "Sem título"
                updated = title if is_standard_date(title) else ""

                projects.append({
                    "id": p_id,
                    "title": title,
                    "url": full_url,
                    "updated": updated,
                })
            return projects
        except Exception as exc:
            if isinstance(exc, FlowError):
                raise
            raise FlowError(f"Erro ao listar projetos: {exc}")

    def get_credits(self) -> dict:
        """Consulta créditos e data de redefinição no modal de Detalhes da conta."""
        page = self._ensure_browser(headless=self.headless)
        try:
            self._goto(page, BASE_URL)
            if "accounts.google.com" in page.url:
                raise FlowError("Sessão não autenticada. Execute 'flow auth login'.")

            btn = page.get_by_role("button", name="Detalhes da conta")
            btn.click(timeout=10000)

            dialog = page.get_by_role("dialog", name="Configurações da conta")
            dialog.wait_for(state="visible", timeout=10000)

            dialog_text = dialog.inner_text() or ""
            credits_val = parse_credits(dialog_text)
            reset_val = parse_reset(dialog_text)

            page.keyboard.press("Escape")
            return {
                "credits": credits_val,
                "reset": reset_val,
            }
        except Exception as exc:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            if isinstance(exc, FlowError):
                raise
            raise FlowError(f"Erro ao consultar créditos: {exc}")

    def list_models(self, kind: str | None = None) -> list[dict]:
        """Lista modelos suportados por inspeção no chip de configuração ou fallback estático."""
        page = self._ensure_browser(headless=self.headless)
        try:
            projects = self.list_projects()
            if not projects:
                models = [m for m in STATIC_MODELS if not kind or m["kind"] == kind]
                return models

            latest_project_url = projects[0]["url"]
            self._goto(page, latest_project_url)

            chip_btn = page.get_by_role("button", name="Gatilho de configurações")
            chip_btn.click(timeout=10000)

            collected = []
            kinds_to_query = [kind] if kind else ["image", "video"]

            for k in ["image", "video"]:
                label = "Imagem" if k == "image" else "Vídeo"
                radio = page.get_by_role("radio", name=label)
                radio.click(force=True)
                time.sleep(1)

                if k in kinds_to_query:
                    sel_btn = page.get_by_role("button", name="Selecionar família de modelos").first
                    sel_btn.click()
                    time.sleep(1.5)

                    raw_text = ""
                    try:
                        overlay = page.locator(".cdk-overlay-pane").last
                        raw_text = overlay.inner_text() or ""
                    except Exception:
                        raw_text = ""

                    if not raw_text.strip():
                        try:
                            raw_text = page.locator("body").inner_text() or ""
                        except Exception:
                            raw_text = ""

                    parsed_names = parse_model_names(raw_text)
                    page.keyboard.press("Escape")
                    time.sleep(0.5)

                    if parsed_names:
                        for name in parsed_names:
                            collected.append({"kind": k, "name": name, "source": "live"})
                    else:
                        for m in STATIC_MODELS:
                            if m["kind"] == k:
                                collected.append(m)

            # Ao final clique no radio 'Imagem' de novo para restaurar e Escape
            try:
                radio_img = page.get_by_role("radio", name="Imagem")
                radio_img.click(force=True)
                time.sleep(0.5)
            except Exception:
                pass
            page.keyboard.press("Escape")

            return collected
        except Exception:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            # Fallback estático documentado
            return [m for m in STATIC_MODELS if not kind or m["kind"] == kind]

    def list_media(self, project_id: str | None = None, kind: str | None = None) -> list[dict]:
        """Lista mídias do projeto ou de todos os projetos."""
        page = self._ensure_browser(headless=self.headless)
        try:
            if project_id:
                p_ids = [project_id]
            else:
                projs = self.list_projects()
                p_ids = [p["id"] for p in projs]

            all_media = []
            for pid in p_ids:
                url = f"https://flow.google.com/project/{pid}"
                self._goto(page, url)

                try:
                    page.wait_for_selector("img[data-media-id]", timeout=10000)
                except Exception:
                    pass

                raw_items = page.eval_on_selector_all(
                    "img[data-media-id]",
                    """imgs => imgs.map(img => {
                        const group = img.closest('[role=group]');
                        let name = group ? group.getAttribute('aria-label') : null;
                        if (!name || !name.trim()) {
                            name = img.getAttribute('alt');
                        }
                        if (!name || !name.trim()) {
                            name = 'Sem título';
                        }
                        const hasVideo = group ? !!group.querySelector('video, [data-icon="play"], button[aria-label*="play" i]') : false;
                        return {
                            id: img.getAttribute('data-media-id') || '',
                            thumbnail: img.getAttribute('src') || '',
                            name: name.trim(),
                            has_video: hasVideo
                        };
                    })"""
                )

                for item in raw_items:
                    m_id = item.get("id") or ""
                    thumb_src = item.get("thumbnail") or ""
                    aria_name = item.get("name") or "Sem título"
                    has_video = bool(item.get("has_video"))

                    item_kind = classify_media(has_video=has_video)
                    if kind and item_kind != kind:
                        continue

                    all_media.append({
                        "id": m_id,
                        "project": pid,
                        "kind": item_kind,
                        "name": aria_name,
                        "thumbnail": thumb_src,
                    })
            return all_media
        except Exception as exc:
            if isinstance(exc, FlowError):
                raise
            raise FlowError(f"Erro ao listar mídias: {exc}")
