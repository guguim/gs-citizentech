from citizentech_vision.address import ParsedAddress
from citizentech_vision.voting import merge_candidates


def candidato(**campos):
    parsed = ParsedAddress(**campos)
    for nome in campos:
        parsed.conf_campo[nome] = (0.9, 0.8)
    return parsed


def test_maioria_decide_cada_campo():
    a = candidato(logradouro="Rua Bardo", cep="01310-100", cidade="São Paulo")
    b = candidato(logradouro="Rua Barão", cep="01310-100", cidade="São Paulo")
    c = candidato(logradouro="Rua Barão", cep="01310-100", cidade="São Paulo")

    resultado, divergentes = merge_candidates([a, b, c])

    assert resultado.logradouro == "Rua Barão"
    assert divergentes == ["logradouro"]


def test_empate_fica_com_o_primeiro_candidato():
    a = candidato(logradouro="Rua A")
    b = candidato(logradouro="Rua B")

    resultado, divergentes = merge_candidates([a, b])

    assert resultado.logradouro == "Rua A"
    assert divergentes == ["logradouro"]


def test_comparacao_ignora_caixa_e_espacos():
    a = candidato(bairro="Centro")
    b = candidato(bairro="CENTRO ")

    _, divergentes = merge_candidates([a, b])

    assert divergentes == []


def test_campo_ausente_em_parte_dos_candidatos_e_divergencia():
    a = candidato(cep="01310-100")
    b = candidato()

    resultado, divergentes = merge_candidates([a, b])

    assert resultado.cep == "01310-100"
    assert divergentes == ["cep"]


def test_campo_vazio_em_todos_nao_e_divergencia():
    resultado, divergentes = merge_candidates([candidato(), candidato()])

    assert divergentes == []
    assert resultado.complemento == ""


def test_confianca_do_campo_vem_do_candidato_escolhido():
    a = ParsedAddress(cep="01310-100")
    a.conf_campo["cep"] = (0.5, 0.4)
    b = ParsedAddress(cep="01310-100")
    b.conf_campo["cep"] = (0.9, 0.8)

    resultado, _ = merge_candidates([a, b])

    assert resultado.conf_campo["cep"] == (0.5, 0.4)
