import shutil
import click
from flow_cli import __version__
from flow_cli.config import get_backend, profile_dir
from flow_cli.output import emit, fail
from flow_cli.browser_utils import FlowError


def _stub(ctx: click.Context, name: str) -> None:
    as_json = bool(ctx.obj and ctx.obj.get("as_json"))
    fail(f"Comando '{name}' ainda não implementado.", as_json=as_json, code=2)


@click.group()
@click.version_option(__version__, "-v", "--version", message="flow-cli %(version)s")
@click.option("--json", "as_json", is_flag=True, default=False, help="Saída em formato JSON.")
@click.pass_context
def main(ctx: click.Context, as_json: bool) -> None:
    """flow - CLI não oficial para o Google Flow."""
    ctx.ensure_object(dict)
    ctx.obj["as_json"] = as_json


# --- auth ---
@main.group()
def auth() -> None:
    """Autenticação e gerenciamento de perfil."""
    pass


@auth.command("login")
@click.pass_context
def auth_login(ctx: click.Context) -> None:
    """Abre navegador para login manual no Google Flow."""
    as_json = bool(ctx.obj and ctx.obj.get("as_json"))
    backend = get_backend(ctx.obj, headless=False)
    try:
        backend.open_login()
        if as_json:
            emit({"logged_in": True}, as_json=True)
        else:
            emit("Login realizado com sucesso no Google Flow.", as_json=False)
    except FlowError as err:
        fail(str(err), as_json=as_json)
    except Exception as exc:
        fail(f"Erro ao abrir login: {exc}", as_json=as_json)
    finally:
        backend.close()


@auth.command("status")
@click.pass_context
def auth_status(ctx: click.Context) -> None:
    """Exibe status da sessão atual."""
    as_json = bool(ctx.obj and ctx.obj.get("as_json"))
    backend = get_backend(ctx.obj, headless=True)
    try:
        logged = backend.is_logged_in()
        if as_json:
            emit({"logged_in": logged}, as_json=True)
        else:
            emit("Logado" if logged else "Não logado", as_json=False)
    finally:
        backend.close()


@auth.command("logout")
@click.option("--yes", is_flag=True, default=False, help="Confirma o encerramento da sessão e remoção do perfil.")
@click.pass_context
def auth_logout(ctx: click.Context, yes: bool) -> None:
    """Encerra a sessão ativa e remove perfil."""
    as_json = bool(ctx.obj and ctx.obj.get("as_json"))
    if not yes:
        fail("Confirmação necessária. Use --yes para encerrar sessão e remover perfil.", as_json=as_json)

    backend = get_backend(ctx.obj)
    try:
        backend.logout()
        p_dir = profile_dir()
        if p_dir.exists():
            shutil.rmtree(p_dir, ignore_errors=True)

        if as_json:
            emit({"logged_out": True}, as_json=True)
        else:
            emit("Sessão encerrada e perfil removido com sucesso.", as_json=False)
    finally:
        backend.close()


# --- projects ---
@main.group()
def projects() -> None:
    """Gerenciamento de projetos."""
    pass


@projects.command("list")
@click.pass_context
def projects_list(ctx: click.Context) -> None:
    """Lista projetos existentes."""
    as_json = bool(ctx.obj and ctx.obj.get("as_json"))
    backend = get_backend(ctx.obj, headless=True)
    try:
        data = backend.list_projects()
        emit(data, as_json=as_json, table_columns=["id", "title", "url"])
    except FlowError as err:
        fail(str(err), as_json=as_json)
    except Exception as exc:
        fail(f"Erro ao listar projetos: {exc}", as_json=as_json)
    finally:
        backend.close()


@projects.command("create")
@click.argument("nome")
@click.pass_context
def projects_create(ctx: click.Context, nome: str) -> None:
    """Cria um novo projeto."""
    _stub(ctx, "projects create")


@projects.command("open")
@click.argument("id")
@click.pass_context
def projects_open(ctx: click.Context, id: str) -> None:
    """Abre projeto no navegador."""
    _stub(ctx, "projects open")


# --- models ---
@main.group()
def models() -> None:
    """Modelos disponíveis para geração."""
    pass


@models.command("list")
@click.option("--kind", type=click.Choice(["image", "video"], case_sensitive=False), help="Filtra por tipo de mídia.")
@click.pass_context
def models_list(ctx: click.Context, kind: str | None) -> None:
    """Lista modelos suportados."""
    as_json = bool(ctx.obj and ctx.obj.get("as_json"))
    backend = get_backend(ctx.obj, headless=True)
    kind_lower = kind.lower() if kind else None
    try:
        data = backend.list_models(kind=kind_lower)
        if kind_lower:
            data = [m for m in data if m.get("kind", "").lower() == kind_lower]
        emit(data, as_json=as_json, table_columns=["kind", "name"])
    except FlowError as err:
        fail(str(err), as_json=as_json)
    except Exception as exc:
        fail(f"Erro ao listar modelos: {exc}", as_json=as_json)
    finally:
        backend.close()


# --- credits ---
@main.command("credits")
@click.pass_context
def credits_cmd(ctx: click.Context) -> None:
    """Consulta créditos disponíveis."""
    as_json = bool(ctx.obj and ctx.obj.get("as_json"))
    backend = get_backend(ctx.obj, headless=True)
    try:
        data = backend.get_credits()
        if as_json:
            emit(data, as_json=True)
        else:
            credits_val = data.get("credits", 0)
            reset_val = data.get("reset")
            output_str = f"Créditos: {credits_val}"
            if reset_val:
                output_str += f"\nRedefinição do limite de uso: {reset_val}"
            emit(output_str, as_json=False)
    except FlowError as err:
        fail(str(err), as_json=as_json)
    except Exception as exc:
        fail(f"Erro ao consultar créditos: {exc}", as_json=as_json)
    finally:
        backend.close()


# --- media ---
@main.group()
def media() -> None:
    """Gerenciamento de mídias geradas."""
    pass


@media.command("list")
@click.option("--project", "project_id", help="Filtra por ID de projeto.")
@click.option("--kind", type=click.Choice(["image", "video"], case_sensitive=False), help="Filtra por tipo de mídia.")
@click.pass_context
def media_list(ctx: click.Context, project_id: str | None, kind: str | None) -> None:
    """Lista mídias do projeto ou gerais."""
    as_json = bool(ctx.obj and ctx.obj.get("as_json"))
    backend = get_backend(ctx.obj, headless=True)
    kind_lower = kind.lower() if kind else None
    try:
        data = backend.list_media(project_id=project_id, kind=kind_lower)
        if kind_lower:
            data = [m for m in data if m.get("kind", "").lower() == kind_lower]
        emit(data, as_json=as_json, table_columns=["id", "project", "kind", "name"])
    except FlowError as err:
        fail(str(err), as_json=as_json)
    except Exception as exc:
        fail(f"Erro ao listar mídias: {exc}", as_json=as_json)
    finally:
        backend.close()


@media.command("download")
@click.argument("id")
@click.option("--out", "out_dir", type=click.Path(), help="Diretório de destino.")
@click.pass_context
def media_download(ctx: click.Context, id: str, out_dir: str | None) -> None:
    """Baixa mídia pelo ID."""
    _stub(ctx, "media download")


# --- generate ---
@main.group()
def generate() -> None:
    """Geração de imagens e vídeos."""
    pass


@generate.command("image")
@click.argument("prompt")
@click.option("--aspect", type=click.Choice(["16:9", "4:3", "1:1", "3:4", "9:16"], case_sensitive=False), default="16:9", show_default=True, help="Proporção da imagem.")
@click.option("--model", help="Nome do modelo.")
@click.option("--count", type=click.IntRange(1, 4), default=1, show_default=True, help="Quantidade de imagens (1 a 4).")
@click.option("--project", "project_id", help="ID do projeto.")
@click.option("--yes", is_flag=True, default=False, help="Confirma o gasto de créditos.")
@click.pass_context
def generate_image(
    ctx: click.Context,
    prompt: str,
    aspect: str,
    model: str | None,
    count: int,
    project_id: str | None,
    yes: bool,
) -> None:
    """Gera imagem a partir do PROMPT."""
    as_json = bool(ctx.obj and ctx.obj.get("as_json"))
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        fail("O prompt não pode ser vazio.", as_json=as_json)

    backend = get_backend(ctx.obj, headless=True)
    try:
        data = backend.generate(
            "image",
            cleaned_prompt,
            project_id=project_id,
            aspect=aspect,
            model=model,
            count=count,
            confirm=yes,
        )
        if as_json:
            emit(data, as_json=True)
        else:
            cost = data.get("cost", 0)
            proj = data.get("project", "")
            if not yes:
                emit(
                    f"Dry-run: esta geração usaria {cost} créditos (projeto {proj}). "
                    f"Nada foi gerado. Use --yes para gerar.",
                    as_json=False,
                )
            else:
                emit(
                    f"Geração enviada: {cost} créditos (projeto {proj}). "
                    f"Acompanhe com `flow media list --project {proj}`.",
                    as_json=False,
                )
    except FlowError as err:
        fail(str(err), as_json=as_json)
    except Exception as exc:
        fail(f"Erro ao gerar imagem: {exc}", as_json=as_json)
    finally:
        backend.close()


@generate.command("video")
@click.argument("prompt")
@click.option("--aspect", type=click.Choice(["16:9", "9:16"], case_sensitive=False), default="16:9", show_default=True, help="Proporção do vídeo.")
@click.option("--model", help="Nome do modelo.")
@click.option("--resolution", type=click.Choice(["360p", "720p"], case_sensitive=False), default="720p", show_default=True, help="Resolução do vídeo.")
@click.option("--duration", type=click.Choice(["4", "6", "8", "10"]), default="4", show_default=True, help="Duração em segundos (4, 6, 8 ou 10).")
@click.option("--count", type=click.IntRange(1, 4), default=1, show_default=True, help="Quantidade de vídeos (1 a 4).")
@click.option("--project", "project_id", help="ID do projeto.")
@click.option("--yes", is_flag=True, default=False, help="Confirma o gasto de créditos.")
@click.pass_context
def generate_video(
    ctx: click.Context,
    prompt: str,
    aspect: str,
    model: str | None,
    resolution: str,
    duration: str,
    count: int,
    project_id: str | None,
    yes: bool,
) -> None:
    """Gera vídeo a partir do PROMPT."""
    as_json = bool(ctx.obj and ctx.obj.get("as_json"))
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        fail("O prompt não pode ser vazio.", as_json=as_json)

    backend = get_backend(ctx.obj, headless=True)
    duration_str = f"{duration}s" if duration and not duration.endswith("s") else duration
    try:
        data = backend.generate(
            "video",
            cleaned_prompt,
            project_id=project_id,
            aspect=aspect,
            model=model,
            resolution=resolution,
            duration=duration_str,
            count=count,
            confirm=yes,
        )
        if as_json:
            emit(data, as_json=True)
        else:
            cost = data.get("cost", 0)
            proj = data.get("project", "")
            if not yes:
                emit(
                    f"Dry-run: esta geração usaria {cost} créditos (projeto {proj}). "
                    f"Nada foi gerado. Use --yes para gerar.",
                    as_json=False,
                )
            else:
                emit(
                    f"Geração enviada: {cost} créditos (projeto {proj}). "
                    f"Acompanhe com `flow media list --project {proj}`.",
                    as_json=False,
                )
    except FlowError as err:
        fail(str(err), as_json=as_json)
    except Exception as exc:
        fail(f"Erro ao gerar vídeo: {exc}", as_json=as_json)
    finally:
        backend.close()


# --- repl ---
@main.command("repl")
@click.pass_context
def repl(ctx: click.Context) -> None:
    """Inicia modo interativo (REPL)."""
    _stub(ctx, "repl")


if __name__ == "__main__":
    main()
