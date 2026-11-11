import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from citizentech_vision import ocr_setup
from citizentech_vision.document import rectify_document
from citizentech_vision.metrics import character_error_rate
from citizentech_vision.ocr import IDIOMA_PADRAO, read_text
from citizentech_vision.preprocess import crop_relative, prepare_for_ocr

DADOS = Path(__file__).resolve().parent.parent / "data"
GABARITO = DADOS / "ground_truth" / "ground_truth.json"


def ocr_disponivel():
    if ocr_setup.find_tesseract() is None:
        return False
    return IDIOMA_PADRAO in ocr_setup.available_languages()


pytestmark = pytest.mark.skipif(
    not ocr_disponivel(), reason="Tesseract com idioma 'por' não disponível"
)


def entrada(id_):
    gabarito = json.loads(GABARITO.read_text(encoding="utf-8"))
    return next(e for e in gabarito if e["id"] == id_)


def test_read_text_le_linha_simples():
    imagem = np.full((120, 900, 3), 255, dtype=np.uint8)
    cv2.putText(imagem, "AV PAULISTA 1578", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 4)

    assert "PAULISTA" in read_text(imagem, psm=7).upper()


def test_read_text_devolve_texto_sem_espacos_nas_pontas():
    imagem = np.full((120, 900, 3), 255, dtype=np.uint8)
    cv2.putText(imagem, "CEP 01310-100", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 4)

    texto = read_text(imagem, psm=7)

    assert texto == texto.strip()


@pytest.mark.skipif(not GABARITO.exists(), reason="dataset sintético não gerado")
@pytest.mark.parametrize("id_", ["enel_01", "sabesp_01", "claro_01"])
def test_ocr_do_endereco_no_documento_limpo(id_):
    dados = entrada(f"{id_}_frontal")
    limpo = cv2.imread(str(DADOS / dados["documento_limpo"]))
    recorte = crop_relative(limpo, dados["regiao_endereco"])

    texto = read_text(recorte)

    assert character_error_rate("\n".join(dados["linhas_impressas"]), texto) < 0.05
    assert dados["endereco"]["cep"] in texto


@pytest.mark.skipif(not GABARITO.exists(), reason="dataset sintético não gerado")
def test_preprocessamento_nao_piora_ocr_de_documento_limpo():
    dados = entrada("enel_01_frontal")
    limpo = cv2.imread(str(DADOS / dados["documento_limpo"]))
    recorte = crop_relative(limpo, dados["regiao_endereco"])
    referencia = "\n".join(dados["linhas_impressas"])

    pronto = prepare_for_ocr(recorte)

    assert character_error_rate(referencia, read_text(pronto)) < 0.05


def cer_do_recorte(id_, preparar):
    dados = entrada(id_)
    foto = cv2.imread(str(DADOS / dados["foto"]))
    limpo = cv2.imread(str(DADOS / dados["documento_limpo"]))
    retificada = rectify_document(foto, tamanho=(limpo.shape[1], limpo.shape[0])).imagem
    recorte = crop_relative(retificada, dados["regiao_endereco"])
    return character_error_rate("\n".join(dados["linhas_impressas"]), read_text(preparar(recorte)))


@pytest.mark.skipif(not GABARITO.exists(), reason="dataset sintético não gerado")
@pytest.mark.parametrize("id_", ["enel_01_dificil", "claro_03_dificil", "sabesp_03_dificil"])
def test_ocr_em_foto_dificil_com_preprocessamento(id_):
    assert cer_do_recorte(id_, prepare_for_ocr) < 0.35


@pytest.mark.skipif(not GABARITO.exists(), reason="dataset sintético não gerado")
def test_preprocessamento_melhora_foto_escura_com_sombra():
    sem = cer_do_recorte("sabesp_03_dificil", lambda im: im)
    com = cer_do_recorte("sabesp_03_dificil", prepare_for_ocr)

    assert com < sem
