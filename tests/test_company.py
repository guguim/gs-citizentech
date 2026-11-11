import json
from pathlib import Path

import cv2
import pytest

from citizentech_vision import ocr_setup
from citizentech_vision.company import identify_company, identify_company_from_text
from citizentech_vision.document import rectify_document
from citizentech_vision.ocr import IDIOMA_PADRAO

DADOS = Path(__file__).resolve().parent.parent / "data"
GABARITO = DADOS / "ground_truth" / "ground_truth.json"


def ocr_disponivel():
    if ocr_setup.find_tesseract() is None:
        return False
    return IDIOMA_PADRAO in ocr_setup.available_languages()


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Enel Distribuição São Paulo CONTA DE ENERGIA ELÉTRICA", "enel"),
        ("Sabesp Nº DA CONTA Companhia de Saneamento Básico - CONTA DE ÁGUA E ESGOTO", "sabesp"),
        ("Sa besp 587481954864 Companhia de Saneamento", "sabesp"),
        ("Claro FATURA DE SERVIÇOS", "claro"),
        ("FATURA DE SERVIÇOS Olívia Gonçalves", "claro"),
    ],
)
def test_identifica_empresa_pelo_texto_do_cabecalho(texto, esperado):
    assert identify_company_from_text(texto).empresa == esperado


@pytest.mark.parametrize("texto", ["", "CONTA DE TELEFONE FIXA", "Nota fiscal de serviços"])
def test_texto_sem_palavras_da_empresa_nao_identifica(texto):
    assert identify_company_from_text(texto) is None


def test_confianca_da_empresa_fica_entre_zero_e_um():
    match = identify_company_from_text("Enel Distribuição São Paulo CONTA DE ENERGIA ELÉTRICA")

    assert 0 < match.confianca <= 1.0
    assert "ENEL" in match.evidencias


@pytest.mark.skipif(not ocr_disponivel(), reason="Tesseract com idioma 'por' não disponível")
@pytest.mark.skipif(not GABARITO.exists(), reason="dataset sintético não gerado")
@pytest.mark.parametrize("id_", ["enel_01_frontal", "sabesp_01_inclinada", "claro_01_frontal", "claro_04_inclinada"])
def test_identifica_empresa_na_foto_retificada(id_):
    entrada = next(e for e in json.loads(GABARITO.read_text(encoding="utf-8")) if e["id"] == id_)
    foto = cv2.imread(str(DADOS / entrada["foto"]))

    pagina = rectify_document(foto).imagem

    assert identify_company(pagina).empresa == entrada["empresa"]
