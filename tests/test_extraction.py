import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from citizentech_vision import ocr_setup
from citizentech_vision.address import CAMPOS
from citizentech_vision.extraction import extract_address
from citizentech_vision.metrics import normalize_text
from citizentech_vision.ocr import IDIOMA_PADRAO

DADOS = Path(__file__).resolve().parent.parent / "data"
GABARITO = DADOS / "ground_truth" / "ground_truth.json"


def ocr_disponivel():
    if ocr_setup.find_tesseract() is None:
        return False
    return IDIOMA_PADRAO in ocr_setup.available_languages()


pytestmark = [
    pytest.mark.skipif(not ocr_disponivel(), reason="Tesseract com idioma 'por' não disponível"),
    pytest.mark.skipif(not GABARITO.exists(), reason="dataset sintético não gerado"),
]


def carregar():
    return {e["id"]: e for e in json.loads(GABARITO.read_text(encoding="utf-8"))}


ENTRADAS = carregar() if GABARITO.exists() else {}
FRONTAIS = [i for i in ENTRADAS if i.endswith("_frontal")]
INCLINADAS = [i for i in ENTRADAS if i.endswith("_inclinada") and i.split("_")[1] in ("01", "02")]


def extrair(id_, metodo="auto"):
    foto = cv2.imread(str(DADOS / ENTRADAS[id_]["foto"]))
    return extract_address(foto, metodo=metodo)


def campos_iguais(esperado, obtido):
    return {c: normalize_text(esperado[c]) == normalize_text(obtido.get(c, "")) for c in CAMPOS}


def digitos(texto):
    return "".join(c for c in texto if c.isdigit())


@pytest.mark.parametrize("id_", FRONTAIS)
def test_foto_frontal_extrai_todos_os_campos_do_gabarito(id_):
    resultado = extrair(id_)

    assert resultado.empresa == ENTRADAS[id_]["empresa"]
    assert all(campos_iguais(ENTRADAS[id_]["endereco"], resultado.campos).values())


@pytest.mark.parametrize("id_", INCLINADAS)
def test_foto_inclinada_extrai_todos_os_campos_do_gabarito(id_):
    resultado = extrair(id_)

    assert all(campos_iguais(ENTRADAS[id_]["endereco"], resultado.campos).values())


@pytest.mark.parametrize("id_", ["enel_01_frontal", "sabesp_01_frontal", "claro_01_frontal"])
def test_metodo_por_ancora_tambem_acha_o_endereco_do_cliente(id_):
    resultado = extrair(id_, metodo="ancora")

    assert resultado.metodo == "ancora"
    assert all(campos_iguais(ENTRADAS[id_]["endereco"], resultado.campos).values())


@pytest.mark.parametrize("id_", FRONTAIS)
def test_endereco_extraido_nunca_e_o_de_agencia_ou_sede(id_):
    resultado = extrair(id_)
    ceps_distratores = {digitos(d.split("CEP")[-1]) for d in ENTRADAS[id_]["enderecos_distratores"]}

    assert digitos(resultado.campos["cep"]) not in ceps_distratores


def test_ancora_nao_confunde_loja_com_endereco_do_cliente_em_foto_dificil():
    id_ = "claro_04_dificil"
    resultado = extrair(id_, metodo="ancora")
    ceps_distratores = {digitos(d.split("CEP")[-1]) for d in ENTRADAS[id_]["enderecos_distratores"]}

    assert digitos(resultado.campos.get("cep", "")) not in ceps_distratores
    assert resultado.precisa_revisao


def test_foto_ilegivel_nao_inventa_endereco_e_pede_revisao():
    resultado = extrair("sabesp_02_dificil")

    assert resultado.precisa_revisao
    assert resultado.confianca < 0.5


def test_imagem_sem_documento_devolve_nao_encontrado_e_pede_revisao():
    imagem = np.full((900, 700, 3), 180, dtype=np.uint8)

    resultado = extract_address(imagem)

    assert not resultado.encontrado
    assert resultado.precisa_revisao
    assert any("não detectada" in p for p in resultado.problemas)


def test_resultado_traz_empresa_metodo_e_campos():
    resultado = extrair("enel_01_frontal")

    assert resultado.empresa == "enel"
    assert resultado.metodo == "zona"
    assert set(resultado.campos) == set(CAMPOS)
    assert resultado.documento.encontrado
