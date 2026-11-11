import json
import random
from pathlib import Path

import cv2
import numpy as np
import pytest

from citizentech_vision.document import (
    DOCUMENT_SIZE,
    detect_document,
    order_corners,
    rectify_document,
    warp_document,
)
from citizentech_vision.metrics import image_similarity, max_corner_error, quad_iou

DADOS = Path(__file__).resolve().parent.parent / "data"
GABARITO = DADOS / "ground_truth" / "ground_truth.json"

SIMILARIDADE_MINIMA = {"frontal": 0.95, "inclinada": 0.9, "dificil": 0.5}


def carregar_amostras():
    if not GABARITO.exists():
        return []
    entradas = json.loads(GABARITO.read_text(encoding="utf-8"))
    return [e for e in entradas if e["id"].split("_")[1] == "01"]


AMOSTRAS = carregar_amostras()
IDS = [e["id"] for e in AMOSTRAS]


def test_order_corners_reordena_pontos_embaralhados():
    esperado = np.array([[100, 50], [400, 60], [410, 500], [90, 490]], dtype=np.float32)
    rng = random.Random(1)
    for _ in range(10):
        embaralhado = esperado.copy().tolist()
        rng.shuffle(embaralhado)
        assert np.allclose(order_corners(embaralhado), esperado)


def test_warp_document_devolve_o_tamanho_pedido():
    imagem = np.random.default_rng(0).integers(0, 255, (800, 600, 3), dtype=np.uint8)
    cantos = [[0, 0], [599, 0], [599, 799], [0, 799]]

    assert warp_document(imagem, cantos).shape == (DOCUMENT_SIZE[1], DOCUMENT_SIZE[0], 3)


def test_warp_document_com_os_proprios_cantos_preserva_a_imagem():
    imagem = np.random.default_rng(0).integers(0, 255, (300, 400, 3), dtype=np.uint8)
    cantos = [[0, 0], [399, 0], [399, 299], [0, 299]]

    resultado = warp_document(imagem, cantos, tamanho=(400, 300))

    assert np.abs(resultado.astype(int) - imagem.astype(int)).mean() < 1


@pytest.mark.parametrize("imagem", [
    np.full((1800, 1300, 3), 120, dtype=np.uint8),
    np.random.default_rng(0).integers(0, 255, (1800, 1300, 3), dtype=np.uint8),
    np.tile(np.linspace(40, 200, 1300, dtype=np.uint8)[None, :, None], (1800, 1, 3)),
], ids=["cinza_liso", "ruido", "gradiente_suave"])
def test_imagem_sem_documento_nao_e_detectada_e_volta_inalterada(imagem):
    resultado = rectify_document(imagem)

    assert not resultado.deteccao.encontrado
    assert not resultado.deteccao.confiavel
    assert resultado.imagem is imagem


@pytest.mark.parametrize("entrada", AMOSTRAS, ids=IDS)
def test_detecta_os_cantos_do_documento_na_foto(entrada):
    foto = cv2.imread(str(DADOS / entrada["foto"]))
    reais = order_corners(np.array(entrada["cantos_documento_foto"], dtype=np.float32))

    deteccao = detect_document(foto)

    assert deteccao.encontrado and deteccao.confiavel
    assert quad_iou(deteccao.cantos, reais) >= 0.95
    assert max_corner_error(deteccao.cantos, reais) <= 15


@pytest.mark.parametrize("entrada", AMOSTRAS, ids=IDS)
def test_documento_corrigido_se_parece_com_o_documento_limpo(entrada):
    foto = cv2.imread(str(DADOS / entrada["foto"]))
    limpo = cv2.imread(str(DADOS / entrada["documento_limpo"]))

    resultado = rectify_document(foto, tamanho=(limpo.shape[1], limpo.shape[0]))

    assert image_similarity(resultado.imagem, limpo) >= SIMILARIDADE_MINIMA[entrada["condicao"]]
