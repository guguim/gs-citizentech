from citizentech_vision.address import ParsedAddress
from citizentech_vision.extraction import LIMIAR_REVISAO, build_result
from citizentech_vision.ocr import Palavra, make_line


def linha(texto, confianca=0.95, y=0):
    palavras = [
        Palavra(p, 10 + i * 60, y, 50, 20, confianca, 1, 1, 1) for i, p in enumerate(texto.split())
    ]
    return make_line(palavras)


def endereco_completo(confianca_minima=0.9):
    parsed = ParsedAddress(
        logradouro="Rua das Flores",
        numero="10",
        bairro="Centro",
        cidade="São Paulo",
        uf="SP",
        cep="01310-100",
        origem={"logradouro": 0, "numero": 0, "bairro": 1, "cidade": 2, "uf": 2, "cep": 2},
    )
    for campo in parsed.origem:
        parsed.conf_campo[campo] = (0.95, confianca_minima)
    return parsed


LINHAS = [linha("RUA DAS FLORES, 10"), linha("CENTRO", y=30), linha("CEP 01310-100 - SAO PAULO - SP", y=60)]


def test_endereco_consistente_e_confiante_nao_pede_revisao():
    resultado = build_result(endereco_completo(), LINHAS, "zona", "enel", None)

    assert resultado.encontrado
    assert not resultado.precisa_revisao
    assert resultado.campos_revisar == []
    assert resultado.confianca >= LIMIAR_REVISAO


def test_cep_ausente_marca_nao_encontrado_e_revisao():
    parsed = endereco_completo()
    parsed.cep = ""

    resultado = build_result(parsed, LINHAS, "zona", "enel", None)

    assert not resultado.encontrado
    assert resultado.precisa_revisao
    assert "cep" in resultado.campos_revisar


def test_palavra_com_baixa_confianca_marca_o_campo():
    resultado = build_result(endereco_completo(confianca_minima=0.3), LINHAS, "zona", "enel", None)

    assert resultado.precisa_revisao
    assert "logradouro" in resultado.campos_revisar


def test_uf_ausente_e_inferida_do_cep_com_aviso():
    parsed = endereco_completo()
    parsed.uf = ""

    resultado = build_result(parsed, LINHAS, "zona", "enel", None)

    assert resultado.campos["uf"] == "SP"
    assert resultado.precisa_revisao
    assert "uf: UF inferida a partir do CEP" in resultado.problemas


def test_divergencia_entre_variantes_marca_o_campo():
    resultado = build_result(endereco_completo(), LINHAS, "zona", "enel", None, divergentes=["bairro"], reforco=True)

    assert "bairro" in resultado.campos_revisar
    assert resultado.reforco


def test_cep_de_outra_uf_marca_revisao():
    parsed = endereco_completo()
    parsed.cep = "20040-020"

    resultado = build_result(parsed, LINHAS, "zona", "enel", None)

    assert resultado.precisa_revisao
    assert any("faixa de SP" in p for p in resultado.problemas)


def test_confianca_cai_com_cada_problema():
    limpo = build_result(endereco_completo(), LINHAS, "zona", "enel", None)
    parsed = endereco_completo()
    parsed.bairro = ""

    com_problema = build_result(parsed, LINHAS, "zona", "enel", None)

    assert com_problema.confianca < limpo.confianca
