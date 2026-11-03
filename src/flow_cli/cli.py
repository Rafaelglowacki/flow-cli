import click
from flow_cli import __version__
from flow_cli.output import fail


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
    _stub(ctx, "auth login")


@auth.command("status")
@click.pass_context
def auth_status(ctx: click.Context) -> None:
    """Exibe status da sessão atual."""
    _stub(ctx, "auth status")


@auth.command("logout")
@click.pass_context
def auth_logout(ctx: click.Context) -> None:
    """Encerra a sessão ativa e remove perfil."""
    _stub(ctx, "auth logout")


# --- projects ---
@main.group()
def projects() -> None:
    """Gerenciamento de projetos."""
    pass


@projects.command("list")
@click.pass_context
def projects_list(ctx: click.Context) -> None:
    """Lista projetos existentes."""
    _stub(ctx, "projects list")


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
    _stub(ctx, "models list")


# --- credits ---
@main.command("credits")
@click.pass_context
def credits_cmd(ctx: click.Context) -> None:
    """Consulta créditos disponíveis."""
    _stub(ctx, "credits")


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
    _stub(ctx, "media list")


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
    _stub(ctx, "generate image")


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
    _stub(ctx, "generate video")


# --- repl ---
@main.command("repl")
@click.pass_context
def repl(ctx: click.Context) -> None:
    """Inicia modo interativo (REPL)."""
    _stub(ctx, "repl")


if __name__ == "__main__":
    main()
