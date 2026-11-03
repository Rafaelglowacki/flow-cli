"""Funções puras de parsing para textos e dados do Google Flow."""
import re
from typing import Literal
from flow_cli.browser_utils import FlowError


def parse_credits(text: str) -> int:
    """Extrai quantidade de créditos a partir de texto (ex: '1.050 créditos do Google Flow', '0 créditos')."""
    if not text:
        raise FlowError("Texto vazio para extração de créditos.")

    # Ex: '1.050 créditos', '25 créditos', '0 créditos'
    match = re.search(r"([\d\.]+)\s+cr[eé]ditos?", text, re.IGNORECASE)
    if not match:
        raise FlowError(f"Não foi possível extrair créditos do texto: '{text}'")

    num_str = match.group(1).replace(".", "")
    try:
        return int(num_str)
    except ValueError:
        raise FlowError(f"Valor numérico inválido de créditos: '{num_str}'")


def parse_cost(text: str) -> int:
    """Extrai custo em créditos a partir de texto (ex: 'A geração vai usar 24 créditos')."""
    if not text:
        raise FlowError("Texto vazio para extração de custo.")

    # Procura 'usar N créditos' ou 'N créditos'
    match = re.search(r"(?:usar\s+)?([\d\.]+)\s+cr[eé]ditos?", text, re.IGNORECASE)
    if not match:
        raise FlowError(f"Não foi possível extrair custo do texto: '{text}'")

    num_str = match.group(1).replace(".", "")
    try:
        return int(num_str)
    except ValueError:
        raise FlowError(f"Valor numérico inválido de custo: '{num_str}'")


def project_id_from_href(href: str | None) -> str | None:
    """Extrai UUID ou ID do projeto a partir de href (ex: '/project/<uuid>', 'https://flow.google.com/project/<uuid>')."""
    if not href:
        return None

    match = re.search(r"/project/([a-zA-Z0-9\-_]+)", href)
    if match:
        return match.group(1)
    return None


def parse_reset(text: str | None) -> str | None:
    """Extrai data/hora de redefinição de uso a partir do texto."""
    if not text:
        return None

    match = re.search(r"Redefinição do limite de uso:\s*([^\r\n]+)", text)
    if match:
        val = match.group(1).strip()
        return val or None

    return None


def is_standard_date(text: str | None) -> bool:
    """Verifica se o texto corresponde ao formato padrão de data de projeto (ex: 'nov. 03 - 15:49')."""
    if not text:
        return False
    return bool(re.match(r"^[a-zA-Z]{3,4}\.?\s+\d{1,2}\s*[-–]\s*\d{1,2}:\d{2}$", text.strip()))


_UUID_REGEX = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def project_url(project_id: str | None) -> str:
    """Valida UUID do projeto e retorna a URL completa no Google Flow."""
    if not project_id or not _UUID_REGEX.match(project_id.strip()):
        raise FlowError(f"ID de projeto inválido: '{project_id}'")
    return f"https://flow.google.com/project/{project_id.strip()}"



def classify_media(has_video: bool) -> Literal["video", "image"]:
    """Classifica tipo de mídia entre video e image."""
    return "video" if has_video else "image"


def parse_model_names(text: str) -> list[str]:
    """Processa texto de overlay/body para extrair nomes de modelos suportados."""
    if not text:
        return []

    target_text = text
    if "A geração vai usar" in target_text:
        # Pega as linhas após o texto 'A geração vai usar'
        lines_after = []
        found = False
        for raw_line in target_text.splitlines():
            if not found:
                if "A geração vai usar" in raw_line:
                    found = True
                continue
            lines_after.append(raw_line)
        target_text = "\n".join(lines_after)

    names: list[str] = []
    for raw_line in target_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "volume_up":
            continue
        if line.startswith("🍌"):
            line = line.lstrip("🍌").strip()
        if line and line not in names:
            names.append(line)
    return names

