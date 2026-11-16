import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from citizentech_vision import ocr_setup
from citizentech_vision.api import (
    CAMPOS_CONTRATO,
    TAMANHO_MAXIMO_BYTES,
    build_response,
    create_app,
    nome_da_empresa,
)
from citizentech_vision.extraction import ExtractionResult
from citizentech_vision.ocr import IDIOMA_PADRAO

DADOS = Path(__file__).resolve().parent.parent / "data"
GABARITO = DADOS / "ground_truth" / "ground_truth.json"

CAMPOS_FAKE = {
    "logradouro": "Rua das Acácias",
    "numero": "120",
    "complemento": "Apto 12",
    "bairro": "Jardim Primavera",
    "cidade": "São Paulo",
    "uf": "SP",
    "cep": "01310-100",
}


def resultado_fake(**alteracoes):
    base = dict(
        encontrado=True,
        empresa="sabesp",
        campos=dict(CAMPOS_FAKE),
        confianca=0.93,
        precisa_revisao=False,
        campos_revisar=[],
        problemas=[],
        metodo="zona",
    )
    base.update(alteracoes)
    return ExtractionResult(**base)


def png_bytes(largura=64, altura=64):
    imagem = np.full((altura, largura, 3), 255, dtype=np.uint8)
    ok, buffer = cv2.imencode(".png", imagem)
    assert ok
    return buffer.tobytes()


def cliente(resultado=None, api_key=""):
    chamadas = []

    def extrator(foto):
        chamadas.append(foto.shape)
        return resultado if resultado is not None else resultado_fake()

    return TestClient(create_app(api_key=api_key, extractor=extrator)), chamadas


def enviar(c, conteudo, tipo="image/png", nome="comprovante.png", headers=None):
    return c.post(
        "/extrair-endereco",
        files={"imagem": (nome, conteudo, tipo)},
        headers=headers or {},
    )


def valida_contrato_zelai(corpo):
    assert set(corpo) >= {"empresa", "confianca", "endereco"}
    assert corpo["empresa"] is None or isinstance(corpo["empresa"], str)
    assert isinstance(corpo["confianca"], (int, float))
    assert 0 <= corpo["confianca"] <= 1
    assert isinstance(corpo["endereco"], dict)
    for campo in CAMPOS_CONTRATO:
        assert campo in corpo["endereco"]
        assert corpo["endereco"][campo] is None or isinstance(corpo["endereco"][campo], str)


def test_health():
    c, _ = cliente()
    resposta = c.get("/health")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


def test_resposta_segue_o_contrato_do_zelai():
    c, chamadas = cliente()
    resposta = enviar(c, png_bytes())
    assert resposta.status_code == 200
    corpo = resposta.json()
    valida_contrato_zelai(corpo)
    assert corpo["empresa"] == "Sabesp"
    assert corpo["confianca"] == 0.93
    assert corpo["endereco"]["logradouro"] == "Rua das Acácias"
    assert corpo["endereco"]["numero"] == "120"
    assert corpo["endereco"]["bairro"] == "Jardim Primavera"
    assert corpo["endereco"]["cep"] == "01310-100"
    assert corpo["endereco"]["cidade"] == "São Paulo"
    assert corpo["revisar"] is False
    assert len(chamadas) == 1


def test_resposta_inclui_campos_extras_para_revisao():
    c, _ = cliente(resultado_fake(
        confianca=0.6,
        precisa_revisao=True,
        campos_revisar=["bairro"],
        problemas=["bairro: palavra com baixa confiança no OCR"],
    ))
    corpo = enviar(c, png_bytes()).json()
    valida_contrato_zelai(corpo)
    assert corpo["revisar"] is True
    assert corpo["campos_revisar"] == ["bairro"]
    assert corpo["problemas"] == ["bairro: palavra com baixa confiança no OCR"]
    assert corpo["endereco"]["complemento"] == "Apto 12"
    assert corpo["endereco"]["uf"] == "SP"


def test_campos_ausentes_viram_nulo():
    campos = {"logradouro": "Rua Rio Branco", "numero": "", "bairro": "  ", "cep": "01001-000"}
    c, _ = cliente(resultado_fake(campos=campos, confianca=0.4, precisa_revisao=True))
    corpo = enviar(c, png_bytes()).json()
    valida_contrato_zelai(corpo)
    assert corpo["endereco"]["numero"] is None
    assert corpo["endereco"]["bairro"] is None
    assert corpo["endereco"]["cidade"] is None


def test_confianca_sempre_entre_zero_e_um():
    assert build_response(resultado_fake(confianca=1.7))["confianca"] == 1.0
    assert build_response(resultado_fake(confianca=-0.2))["confianca"] == 0.0


@pytest.mark.parametrize("bruto,esperado", [
    ("enel", "Enel"),
    ("sabesp", "Sabesp"),
    ("claro", "Claro"),
    (None, None),
    ("", None),
    ("outra empresa", "Outra Empresa"),
])
def test_nome_da_empresa(bruto, esperado):
    assert nome_da_empresa(bruto) == esperado


def test_empresa_nao_identificada_vira_nulo():
    c, _ = cliente(resultado_fake(empresa=None))
    corpo = enviar(c, png_bytes()).json()
    valida_contrato_zelai(corpo)
    assert corpo["empresa"] is None


def test_sem_chave_configurada_nao_exige_header():
    c, _ = cliente(api_key="")
    assert enviar(c, png_bytes()).status_code == 200


def test_chave_correta_e_aceita():
    c, _ = cliente(api_key="segredo")
    assert enviar(c, png_bytes(), headers={"x-api-key": "segredo"}).status_code == 200


@pytest.mark.parametrize("headers", [{}, {"x-api-key": "errada"}, {"x-api-key": ""}])
def test_chave_ausente_ou_errada_e_recusada(headers):
    c, chamadas = cliente(api_key="segredo")
    resposta = enviar(c, png_bytes(), headers=headers)
    assert resposta.status_code == 401
    assert chamadas == []


def test_health_nao_exige_chave():
    c, _ = cliente(api_key="segredo")
    assert c.get("/health").status_code == 200


def test_tipo_nao_suportado_e_recusado():
    c, chamadas = cliente()
    resposta = enviar(c, b"%PDF-1.4", tipo="application/pdf", nome="conta.pdf")
    assert resposta.status_code == 415
    assert chamadas == []


def test_imagem_acima_do_limite_e_recusada():
    c, chamadas = cliente()
    resposta = enviar(c, b"\x00" * (TAMANHO_MAXIMO_BYTES + 1))
    assert resposta.status_code == 413
    assert chamadas == []


def test_arquivo_corrompido_e_recusado():
    c, chamadas = cliente()
    resposta = enviar(c, b"isto nao e uma imagem")
    assert resposta.status_code == 422
    assert chamadas == []


def test_campo_imagem_obrigatorio():
    c, _ = cliente()
    resposta = c.post("/extrair-endereco", files={"outro": ("a.png", png_bytes(), "image/png")})
    assert resposta.status_code == 422


def test_endereco_nao_encontrado_devolve_422():
    c, _ = cliente(ExtractionResult(encontrado=False))
    resposta = enviar(c, png_bytes())
    assert resposta.status_code == 422


def test_aceita_jpeg_e_webp():
    imagem = np.full((32, 32, 3), 200, dtype=np.uint8)
    for extensao, tipo in ((".jpg", "image/jpeg"), (".webp", "image/webp")):
        ok, buffer = cv2.imencode(extensao, imagem)
        assert ok
        c, _ = cliente()
        assert enviar(c, buffer.tobytes(), tipo=tipo, nome=f"a{extensao}").status_code == 200


def test_nada_e_gravado_em_disco(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    c, _ = cliente()
    enviar(c, png_bytes())
    assert list(tmp_path.iterdir()) == []


def ocr_disponivel():
    if ocr_setup.find_tesseract() is None:
        return False
    return IDIOMA_PADRAO in ocr_setup.available_languages()


@pytest.mark.skipif(not ocr_disponivel(), reason="Tesseract com idioma 'por' não disponível")
@pytest.mark.skipif(not GABARITO.exists(), reason="dataset sintético não gerado")
def test_ponta_a_ponta_com_foto_sintetica():
    entradas = {e["id"]: e for e in json.loads(GABARITO.read_text(encoding="utf-8"))}
    entrada = entradas["sabesp_01_frontal"]
    c = TestClient(create_app(api_key="segredo"))
    conteudo = (DADOS / entrada["foto"]).read_bytes()
    resposta = enviar(c, conteudo, tipo="image/jpeg", nome="foto.jpg", headers={"x-api-key": "segredo"})
    assert resposta.status_code == 200
    corpo = resposta.json()
    valida_contrato_zelai(corpo)
    assert corpo["empresa"] == "Sabesp"
    assert corpo["endereco"]["cep"].replace("-", "") == entrada["endereco"]["cep"].replace("-", "")
