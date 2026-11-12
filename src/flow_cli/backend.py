"""Backends de automação e comunicação com o Flow."""
from abc import ABC, abstractmethod
from pathlib import Path
import re
import shutil
import time
from typing import Any
from flow_cli.browser_utils import FlowError
from flow_cli.parsers import (
    parse_credits,
    parse_cost,
    project_id_from_href,
    project_url,
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
        """Configura e submete ou simula geração."""
        raise FlowError("não suportado por este backend")

    def download_media(self, media_id: str, out_dir: Path, project_id: str | None = None) -> dict:
        """Baixa mídia pelo ID."""
        raise FlowError("não suportado por este backend")

    def create_project(self, name: str | None = None) -> dict:
        """Cria um novo projeto."""
        raise FlowError("não suportado por este backend")

    def project_url(self, project_id: str) -> str:
        """Retorna a URL completa do projeto."""
        return project_url(project_id)



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
        launch_kwargs: dict[str, Any] = {
            "user_data_dir": str(self.profile_path),
            "headless": is_headless,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"],
        }
        if shutil.which("google-chrome") or shutil.which("google-chrome-stable"):
            launch_kwargs["channel"] = "chrome"
            launch_kwargs["ignore_default_args"] = ["--password-store=basic"]
        self._context = self._playwright.chromium.launch_persistent_context(**launch_kwargs)
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
        try:
            btn = page.get_by_role("button", name=re.compile(r"Crie com o Google Flow|Create with Google Flow", re.I))
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click(timeout=5000)
                time.sleep(3)
        except Exception:
            pass

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
                if kind in (None, "video"):
                    all_media.extend(self._list_video_tiles(page, pid, url))
            return all_media
        except Exception as exc:
            if isinstance(exc, FlowError):
                raise
            raise FlowError(f"Erro ao listar mídias: {exc}")

    def _list_video_tiles(self, page: Any, pid: str, url: str) -> list[dict]:
        """Vídeos não têm data-media-id: o id vem da URL /edit/<id> ao abrir cada cartão."""
        try:
            self._goto(page, url)
            tiles = page.locator("flow-video-tile")
            tiles.first.wait_for(timeout=4000)
        except Exception:
            return []
        found = []
        for idx in range(tiles.count()):
            if idx:
                self._goto(page, url)
                tiles.first.wait_for(timeout=8000)
            tile = tiles.nth(idx)
            name = ""
            try:
                grp = tile.locator("xpath=ancestor::*[@role='group'][1]")
                name = (grp.first.get_attribute("aria-label") or "").strip()
            except Exception:
                pass
            thumb = ""
            try:
                thumb = tile.locator("img").first.get_attribute("src") or ""
            except Exception:
                pass
            tile.click(timeout=5000)
            try:
                page.wait_for_url(re.compile(r"/edit/[0-9a-f-]{36}"), timeout=10000)
            except Exception:
                continue
            m = re.search(r"/edit/([0-9a-f-]{36})", page.url)
            if m:
                found.append({"id": m.group(1), "project": pid, "kind": "video",
                              "name": name or "Sem título", "thumbnail": thumb})
        return found

    def _download_via_edit_page(self, page: Any, project_id: str, media_id: str, out_dir: Path) -> dict:
        """Baixa mídia (vídeo) pela página /edit/<id> usando o botão 'Baixar mídia'."""
        self._goto(page, f"https://flow.google.com/project/{project_id}/edit/{media_id}")
        btn = page.get_by_role("button", name="Baixar mídia")
        btn.first.wait_for(timeout=15000)
        with page.expect_download(timeout=60000) as info:
            btn.first.click(timeout=5000)
            try:
                orig = page.get_by_role("menuitem").filter(has_text="Tamanho original")
                orig.first.wait_for(timeout=3000)
                orig.first.click(timeout=3000)
            except Exception:
                pass
        download = info.value
        name = download.suggested_filename or f"{media_id}.mp4"
        target = Path(out_dir) / name
        download.save_as(str(target))
        size = target.stat().st_size
        if size == 0:
            raise FlowError("Download vazio.")
        return {"id": media_id, "path": str(target), "bytes": size, "kind": "video"}

    def _submit_generation(self, page: Any, confirm: bool) -> None:
        """Submete a geração clicando em 'Iniciar geração'. Isolado e protegido por confirm=True."""
        if not confirm:
            raise FlowError("Confirmação necessária para envio de geração. Clique abortado.")
        submit_btn = page.get_by_role("button", name="Iniciar geração")
        submit_btn.click()

    def _read_generation_cost(self, page: Any) -> int:
        """Lê o custo de geração de forma estável, tentando elemento de configurações, overlay e body."""
        last_cost: int | None = None

        for attempt in range(6):
            if attempt > 0:
                time.sleep(0.7)

            popup_text = ""
            # Elemento do popup de configurações
            try:
                elem = page.locator("flow-prompt-box-settings").first
                popup_text = elem.inner_text() or ""
            except Exception:
                popup_text = ""

            # Fallback para o overlay
            if not popup_text or "crédito" not in popup_text.lower():
                try:
                    overlay = page.locator(".cdk-overlay-pane").last
                    popup_text = overlay.inner_text() or ""
                except Exception:
                    popup_text = ""

            # Fallback para body
            if not popup_text or "crédito" not in popup_text.lower():
                try:
                    popup_text = page.locator("body").inner_text() or ""
                except Exception:
                    popup_text = ""

            try:
                current_cost = parse_cost(popup_text)
            except Exception:
                current_cost = None

            if current_cost is not None:
                if last_cost is not None and current_cost == last_cost:
                    return current_cost
                last_cost = current_cost

        if last_cost is not None:
            return last_cost

        raise FlowError(f"Falha ao ler custo de geração: texto '{popup_text}' não contém custo válido")

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
        """Configura o chip, preenche o prompt, lê o custo e envia se confirm for True."""
        page = self._ensure_browser(headless=self.headless)
        try:
            # 1. Resolve projeto
            target_project_id = project_id
            if not target_project_id:
                projects = self.list_projects()
                if not projects:
                    raise FlowError("Nenhum projeto encontrado para geração.")
                target_project_id = projects[0]["id"]

            project_url = f"{BASE_URL}project/{target_project_id}"
            self._goto(page, project_url)

            # 2. Abre popup de configurações
            chip_btn = page.get_by_role("button", name="Gatilho de configurações")
            chip_btn.click(timeout=10000)

            # 3. Seleciona tipo (Imagem ou Vídeo)
            kind_label = "Imagem" if kind.lower() == "image" else "Vídeo"
            page.get_by_role("radio", name=kind_label).click(force=True)

            # 4. Aspecto
            if aspect:
                page.get_by_role("radio", name=aspect, exact=True).click(force=True)

            # 5. Modelo
            if model:
                sel_btn = page.get_by_role("button", name="Selecionar família de modelos").first
                sel_btn.click()
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

                available_models = parse_model_names(raw_text)
                clean_target = model.strip().lower()
                matched_model = None
                for candidate in available_models:
                    if clean_target in candidate.lower():
                        matched_model = candidate
                        break

                if not matched_model:
                    page.keyboard.press("Escape")
                    avail_str = ", ".join(f"'{m}'" for m in available_models)
                    raise FlowError(f"Modelo '{model}' não encontrado. Disponíveis: {avail_str or 'nenhum'}")

                # Clica no item do overlay cujo texto contenha o nome
                item_locator = page.locator(".cdk-overlay-pane").last.locator(f"text={matched_model}").first
                try:
                    item_locator.click()
                except Exception:
                    page.locator(f"text={matched_model}").first.click()
                time.sleep(1.0)

            # 6. Opções específicas de vídeo
            if kind.lower() == "video":
                if resolution:
                    try:
                        page.get_by_role("radio", name=resolution, exact=True).click(force=True, timeout=3000)
                    except Exception:
                        pass
                if duration:
                    # '4s', '6s', '8s', '10s'
                    try:
                        page.get_by_role("radio", name=duration, exact=True).click(force=True, timeout=3000)
                    except Exception:
                        pass

            # 7. Quantidade
            if count:
                page.get_by_role("radio", name=f"x{count}", exact=True).click(force=True)

            # Espera 1.5s após o último clique de opção para UI atualizar
            time.sleep(1.5)

            # 8. Lê custo no popup de forma estável
            try:
                cost = self._read_generation_cost(page)
            except Exception as exc:
                page.keyboard.press("Escape")
                raise FlowError(f"Falha ao ler custo de geração: {exc}")

            # Fecha popup de configurações
            page.keyboard.press("Escape")

            # 9. Preenche prompt
            prompt_box = page.get_by_role("textbox", name="O que você quer criar?")
            prompt_box.fill(prompt)

            # 10. Envia ou dry-run
            if confirm:
                self._submit_generation(page, confirm=True)
                time.sleep(3)
                submitted = True
                dry_run = False
            else:
                prompt_box.fill("")
                submitted = False
                dry_run = True

            result_dict = {
                "kind": kind,
                "project": target_project_id,
                "model": model,
                "aspect": aspect,
                "count": count,
                "cost": cost,
                "submitted": submitted,
                "dry_run": dry_run,
            }
            if kind.lower() == "video":
                result_dict["resolution"] = resolution
                result_dict["duration"] = duration

            return result_dict

        except Exception as exc:
            if isinstance(exc, FlowError):
                raise
            raise FlowError(f"Erro ao gerar {kind}: {exc}")

    def create_project(self, name: str | None = None) -> dict:
        """Cria um novo projeto via interface."""
        page = self._ensure_browser(headless=self.headless)
        try:
            self._goto(page, BASE_URL)
            btn_new = page.get_by_role("button", name="Novo projeto")
            btn_new.click(timeout=10000)

            page.wait_for_url(re.compile(r"/project/[0-9a-f-]{36}"), timeout=30000)
            current_url = page.url
            proj_id = project_id_from_href(current_url)
            if not proj_id:
                match = re.search(r"/project/([0-9a-f-]{36})", current_url)
                proj_id = match.group(1) if match else None

            if not proj_id:
                raise FlowError("Falha ao obter ID do novo projeto criado.")

            final_title = "Sem título"
            if name:
                # Clica no heading ou textbox editável e preenche com Enter apenas nele
                title_box = page.get_by_role("textbox", name="Texto editável")
                try:
                    has_box = bool(title_box.count() > 0)
                except Exception:
                    has_box = False

                if not has_box:
                    try:
                        title_heading = page.get_by_role("heading", level=1)
                        if title_heading.count() > 0:
                            title_heading.first.click(timeout=5000)
                    except Exception:
                        pass

                try:
                    if title_box.count() > 0:
                        title_box.first.fill(name)
                        title_box.first.press("Enter")
                except Exception:
                    pass
                final_title = name
            else:
                try:
                    h1 = page.get_by_role("heading", level=1).first
                    final_title = (h1.inner_text() or "").strip() or "Sem título"
                except Exception:
                    pass

            return {
                "id": proj_id,
                "title": final_title,
                "url": f"https://flow.google.com/project/{proj_id}",
            }
        except Exception as exc:
            if isinstance(exc, FlowError):
                raise
            raise FlowError(f"Erro ao criar projeto: {exc}")

    def download_media(self, media_id: str, out_dir: Path, project_id: str | None = None) -> dict:
        """Localiza e baixa mídia para out_dir."""
        page = self._ensure_browser(headless=self.headless)
        try:
            if project_id:
                p_ids = [project_id]
            else:
                projs = self.list_projects()
                p_ids = [p["id"] for p in projs]

            media_img = None
            found_proj = None

            for pid in p_ids:
                url = f"https://flow.google.com/project/{pid}"
                self._goto(page, url)
                try:
                    page.wait_for_selector("img[data-media-id]", timeout=10000)
                except Exception:
                    pass

                target_sel = f'img[data-media-id="{media_id}"]'
                loc = page.locator(target_sel)
                if loc.count() > 0:
                    media_img = loc.first
                    found_proj = pid
                    break

            if media_img is None and project_id:
                Path(out_dir).mkdir(parents=True, exist_ok=True)
                try:
                    return self._download_via_edit_page(page, project_id, media_id, out_dir)
                except FlowError:
                    raise
                except Exception:
                    pass
            if media_img is None:
                raise FlowError(f"Mídia '{media_id}' não encontrada em nenhum projeto verificado (para vídeos use --project).")

            # Verifica se cartão tem tag video ou ícone de play
            group = media_img.locator("xpath=ancestor::*[@role='group'][1]")
            has_video = False
            video_src = None
            try:
                has_group = bool(group.count() > 0)
            except Exception:
                has_group = False

            if has_group:
                try:
                    video_loc = group.locator("video, [data-icon='play'], button[aria-label*='play' i]")
                    has_video = bool(video_loc.count() > 0)
                except Exception:
                    has_video = False

                if has_video:
                    try:
                        v_elem = group.locator("video")
                        if v_elem.count() > 0:
                            video_src = v_elem.first.get_attribute("src")
                    except Exception:
                        pass


            out_dir = Path(out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

            if not has_video:
                # Imagem
                src = media_img.get_attribute("src") or ""
                if not src:
                    raise FlowError(f"URL de imagem não encontrada para mídia '{media_id}'.")

                if "=" in src:
                    original_url = src.rsplit("=", 1)[0] + "=d"
                else:
                    original_url = src

                response = self._context.request.get(original_url)
                if response.status != 200:
                    raise FlowError(f"Falha ao baixar imagem: status HTTP {response.status}")

                body_bytes = response.body()
                if not body_bytes:
                    raise FlowError("Falha ao baixar imagem: corpo da resposta vazio.")

                content_type = response.headers.get("content-type", "").lower()
                ext = ".jpg"
                if "png" in content_type:
                    ext = ".png"
                elif "webp" in content_type:
                    ext = ".webp"

                target_file = out_dir / f"{media_id}{ext}"
                target_file.write_bytes(body_bytes)

                return {
                    "id": media_id,
                    "path": str(target_file),
                    "bytes": len(body_bytes),
                    "kind": "image",
                }
            else:
                # Vídeo
                if video_src:
                    response = self._context.request.get(video_src)
                    if response.status == 200 and response.body():
                        body_bytes = response.body()
                        target_file = out_dir / f"{media_id}.mp4"
                        target_file.write_bytes(body_bytes)
                        return {
                            "id": media_id,
                            "path": str(target_file),
                            "bytes": len(body_bytes),
                            "kind": "video",
                        }

                # Fallback vídeo via download button na UI
                card = group if group.count() > 0 else media_img
                card.click(timeout=5000)

                with page.expect_download(timeout=30000) as download_info:
                    btn_download = page.get_by_role("button", name="Baixar mídia")
                    if btn_download.count() > 0:
                        btn_download.first.click(timeout=5000)
                    else:
                        raise FlowError("Botão 'Baixar mídia' não encontrado na interface.")

                    # Se aparecer menu suspenso de download, escolhe primeiro item
                    try:
                        menu_items = page.get_by_role("menuitem")
                        if menu_items.count() > 0:
                            menu_items.first.click(timeout=3000)
                    except Exception:
                        pass

                download = download_info.value
                suggested_filename = download.suggested_filename or f"{media_id}.mp4"
                target_file = out_dir / suggested_filename
                download.save_as(str(target_file))

                file_bytes = target_file.stat().st_size if target_file.exists() else 0
                return {
                    "id": media_id,
                    "path": str(target_file),
                    "bytes": file_bytes,
                    "kind": "video",
                }

        except Exception as exc:
            if isinstance(exc, FlowError):
                raise
            raise FlowError(f"Erro ao baixar mídia: {exc}")

