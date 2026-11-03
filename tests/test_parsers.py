import pytest
from flow_cli.browser_utils import FlowError
from flow_cli.parsers import (
    parse_credits,
    parse_cost,
    project_id_from_href,
    parse_reset,
    classify_media,
    is_standard_date,
    parse_model_names,
)


def test_parse_credits():
    assert parse_credits("1.050 créditos do Google Flow") == 1050
    assert parse_credits("0 créditos") == 0
    assert parse_credits("25 créditos restantes") == 25
    assert parse_credits("10.500 créditos") == 10500

    with pytest.raises(FlowError):
        parse_credits("sem créditos aqui")

    with pytest.raises(FlowError):
        parse_credits("")


def test_parse_cost():
    assert parse_cost("A geração vai usar 24 créditos") == 24
    assert parse_cost("geração vai usar 0 créditos") == 0
    assert parse_cost("vai usar 150 créditos") == 150

    with pytest.raises(FlowError):
        parse_cost("sem informação de custo")


def test_project_id_from_href():
    assert project_id_from_href("/project/123e4567-e89b-12d3-a456-426614174000") == "123e4567-e89b-12d3-a456-426614174000"
    assert project_id_from_href("/project/abc-xyz") == "abc-xyz"
    assert project_id_from_href("/project/123?param=val") == "123"
    assert project_id_from_href("https://flow.google.com/project/xyz-789") == "xyz-789"
    assert project_id_from_href("/other/path") is None
    assert project_id_from_href(None) is None


def test_parse_reset():
    assert parse_reset("Redefinição do limite de uso: 20 de nov., 20:08") == "20 de nov., 20:08"
    assert parse_reset("Redefinição do limite de uso: amanhã, 12:00") == "amanhã, 12:00"
    assert parse_reset("outro texto qualquer") is None
    assert parse_reset("") is None


def test_parse_reset_multiline_with_garbage():
    multiline = (
        "Configurações da conta\n"
        "1.050 créditos do Google Flow\n"
        "Redefinição do limite de uso: 20 de nov., 20:08\n"
        "Sair de todas as contas\n"
        "frame_spark\n"
        "Marca-d'água visível\n"
        "Privacidade."
    )
    assert parse_reset(multiline) == "20 de nov., 20:08"


def test_is_standard_date():
    assert is_standard_date("nov. 03 - 15:49") is True
    assert is_standard_date(" nov. 03 - 15:49 ") is True
    assert is_standard_date("nov. 03 - 10:00") is True
    assert is_standard_date("out. 25 - 14:20") is True
    assert is_standard_date("Projeto Alfa") is False
    assert is_standard_date("Sem título") is False
    assert is_standard_date("") is False
    assert is_standard_date(None) is False


def test_classify_media():
    assert classify_media(has_video=True) == "video"
    assert classify_media(has_video=False) == "image"


def test_parse_model_names_image():
    raw_overlay = """
    volume_up
    🍌 Nano Banana Pro
    
    🍌 Nano Banana 2 Lite
    volume_up
    🍌 Nano Banana 2.1
    """
    assert parse_model_names(raw_overlay) == [
        "Nano Banana Pro",
        "Nano Banana 2 Lite",
        "Nano Banana 2.1",
    ]


def test_parse_model_names_video():
    raw_overlay = """
    Omni 1.1 Flash
    volume_up
    Veo 3.1 - Lite
    Veo 3.1 - Fast
    Veo 3.1 - Quality
    """
    assert parse_model_names(raw_overlay) == [
        "Omni 1.1 Flash",
        "Veo 3.1 - Lite",
        "Veo 3.1 - Fast",
        "Veo 3.1 - Quality",
    ]


def test_parse_model_names_fallback_body_with_prefix():
    raw_body = """
    Outro conteúdo antes
    A geração vai usar 20 créditos
    volume_up
    🍌 Nano Banana Pro
    🍌 Nano Banana 2 Lite
    """
    assert parse_model_names(raw_body) == [
        "Nano Banana Pro",
        "Nano Banana 2 Lite",
    ]


def test_parse_model_names_empty():
    assert parse_model_names("") == []
    assert parse_model_names("   \nvolume_up\n   ") == []

