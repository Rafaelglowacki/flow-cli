"""Configurações, caminhos e injeção de dependência de backend."""
import os
from pathlib import Path
from typing import Any
from flow_cli.backend import Backend, PlaywrightBackend

_BACKEND_FACTORY = None


def profile_dir() -> Path:
    """Retorna diretório de perfil configurado por FLOW_CLI_PROFILE_DIR ou padrão."""
    env_dir = os.environ.get("FLOW_CLI_PROFILE_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    return Path.home() / ".config" / "flow-cli" / "profile"


def set_backend_factory(factory: Any) -> None:
    """Substitui a fábrica de backend (útil para testes globais)."""
    global _BACKEND_FACTORY
    _BACKEND_FACTORY = factory


def get_backend(ctx_obj: dict[str, Any] | None = None, headless: bool = True) -> Backend:
    """Retorna backend injetado via ctx.obj, fábrica global ou PlaywrightBackend padrão."""
    if ctx_obj and "backend" in ctx_obj:
        return ctx_obj["backend"]
    if _BACKEND_FACTORY is not None:
        return _BACKEND_FACTORY(headless=headless)
    return PlaywrightBackend(profile_path=profile_dir(), headless=headless)
