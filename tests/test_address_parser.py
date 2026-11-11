import pytest

from citizentech_vision.address import (
    expand_complement,
    expand_street_type,
    is_complement,
    parse_address_lines,
    smart_title,
)


def campos(linhas):
    return parse_address_lines(linhas).as_dict()


def test_formato_enel_tres_linhas_em_maiusculas():
    resultado = campos(
        [
            "TRAVESSA MARECHAL DEODORO, 108",
            "VILA INDUSTRIAL",
            "CEP 09819-597 - SÃO BERNARDO DO CAMPO - SP",
        ]
    )

    assert resultado == {
        "logradouro": "Travessa Marechal Deodoro",
        "numero": "108",
        "complemento": "",
        "bairro": "Vila Industrial",
        "cidade": "São Bernardo do Campo",
        "uf": "SP",
        "cep": "09819-597",
    }


def test_formato_enel_com_complemento_na_primeira_linha():
    resultado = campos(
        ["AVENIDA DOM PEDRO II, 2965 - BLOCO B APTO 136", "CENTRO", "CEP 01310-100 - SÃO PAULO - SP"]
    )

    assert resultado["complemento"] == "Bloco B Apto 136"
    assert resultado["bairro"] == "Centro"
    assert resultado["logradouro"] == "Avenida Dom Pedro II"


def test_formato_sabesp_abreviado_em_duas_linhas():
    resultado = campos(["AV CASTRO ALVES, 233 CS 143 - CENTRO", "SÃO PAULO - SP - 01591-694"])

    assert resultado["logradouro"] == "Avenida Castro Alves"
    assert resultado["numero"] == "233"
    assert resultado["complemento"] == "Casa 143"
    assert resultado["bairro"] == "Centro"
    assert resultado["cidade"] == "São Paulo"
    assert resultado["uf"] == "SP"
    assert resultado["cep"] == "01591-694"


def test_formato_sabesp_sem_complemento():
    resultado = campos(["R DAS FLORES, 40 - JARDIM AMÉRICA", "OSASCO - SP - 06010-100"])

    assert resultado["logradouro"] == "Rua das Flores"
    assert resultado["complemento"] == ""
    assert resultado["bairro"] == "Jardim América"


def test_formato_claro_bairro_e_cidade_na_mesma_linha():
    resultado = campos(
        ["Rua Barão de Itapetininga, 2480 - Casa 37", "Centro - São Paulo/SP", "CEP 02789-365"]
    )

    assert resultado["logradouro"] == "Rua Barão de Itapetininga"
    assert resultado["complemento"] == "Casa 37"
    assert resultado["bairro"] == "Centro"
    assert resultado["cidade"] == "São Paulo"
    assert resultado["uf"] == "SP"
    assert resultado["cep"] == "02789-365"


def test_ignora_rotulo_e_linhas_antes_do_logradouro():
    resultado = campos(
        [
            "ENDEREÇO DA UNIDADE CONSUMIDORA",
            "RUA TIRADENTES, 55",
            "MOOCA",
            "CEP 03101-000 - SÃO PAULO - SP",
        ]
    )

    assert resultado["logradouro"] == "Rua Tiradentes"
    assert resultado["bairro"] == "Mooca"


def test_cep_com_separador_trocado_pelo_ocr():
    resultado = campos(["Rua A, 10", "Centro - Campinas/SP", "CEP 13041:093"])

    assert resultado["cep"] == "13041-093"


def test_separador_confuso_entre_bairro_e_cidade():
    resultado = campos(["Travessa Padre Anchieta, 2801", "Parque São Jorge « Campinas/SP", "CEP 13041-093"])

    assert resultado["bairro"] == "Parque São Jorge"
    assert resultado["cidade"] == "Campinas"


def test_cidade_corrigida_pela_lista_de_cidades_conhecidas():
    resultado = campos(["Rua A, 10", "Centro - Sho Paulo/SP", "CEP 01310-100"])

    assert resultado["cidade"] == "São Paulo"


def test_uf_colada_na_cidade_deixa_uf_vazia_e_gera_aviso():
    parsed = parse_address_lines(["Rua A, 10", "Vila Mariana - Santo AndráysP", "CEP 09048-553"])

    assert parsed.cidade == "Santo André"
    assert parsed.uf == ""
    assert ("uf", "UF não encontrada no texto") in parsed.avisos


def test_numero_sem_virgula_gera_marca():
    parsed = parse_address_lines(["Rua Dom Pedro 577", "Centro - São Paulo/SP", "CEP 01310-100"])

    assert parsed.numero == "577"
    assert parsed.sem_virgula


def test_numero_sem_numero():
    resultado = campos(["Rodovia Anhanguera, S/N", "Centro - Osasco/SP", "CEP 06010-100"])

    assert resultado["numero"] == "S/N"


def test_algarismo_romano_lido_como_letras_e_corrigido():
    resultado = campos(["Rua Dom Pedro Il, 577", "Centro - São Paulo/SP", "CEP 01310-100"])

    assert resultado["logradouro"] == "Rua Dom Pedro II"


def test_euro_lido_no_lugar_de_c_no_complemento():
    resultado = campos(["AV CASTRO ALVES, 233 €S 143 - CENTRO", "SÃO PAULO - SP - 01591-694"])

    assert resultado["complemento"] == "Casa 143"


def test_complemento_irreconhecivel_gera_aviso():
    parsed = parse_address_lines(["AL JOSE BONIFACIO, 773 BL BAP 174 - VILA ESPERANCA", "SÃO PAULO - SP - 01591-694"])

    assert parsed.bairro == "Vila Esperanca"
    assert ("complemento", "formato do complemento não reconhecido") in parsed.avisos


def test_sem_logradouro_devolve_tudo_vazio():
    resultado = campos(["ENDEREÇO DO IMÓVEL", "xx"])

    assert not any(resultado.values())


def test_origem_das_linhas_para_confianca():
    parsed = parse_address_lines(["ROTULO LONGO", "RUA A, 10", "BAIRRO X", "CEP 01310-100 - SÃO PAULO - SP"])

    assert parsed.origem["logradouro"] == 1
    assert parsed.origem["bairro"] == 2
    assert parsed.origem["cep"] == 3


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("APTO 12", True),
        ("BL A AP 12", True),
        ("CS 37", True),
        ("FDS", True),
        ("SL 5", True),
        ("Casa Verde", False),
        ("Centro", False),
    ],
)
def test_is_complement(texto, esperado):
    assert is_complement(texto) is esperado


def test_expansoes_de_abreviacoes():
    assert expand_street_type("AV Castro Alves") == "Avenida Castro Alves"
    assert expand_street_type("Rua das Flores") == "Rua das Flores"
    assert expand_complement("BL A AP 12") == "Bloco A Apto 12"


def test_smart_title_preserva_romanos_preposicoes_e_texto_misto():
    assert smart_title("RUA XV DE NOVEMBRO") == "Rua XV de Novembro"
    assert smart_title("AVENIDA DOM PEDRO II") == "Avenida Dom Pedro II"
    assert smart_title("Rua Barão de Itapetininga") == "Rua Barão de Itapetininga"
    assert smart_title("BLOCO A") == "Bloco A"
