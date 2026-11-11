import pytest

from citizentech_vision.validation import (
    fields_to_review,
    infer_state,
    suspicious_words,
    uf_from_zip,
    validate_address,
)


def endereco(**alteracoes):
    base = {
        "logradouro": "Rua das Flores",
        "numero": "10",
        "complemento": "",
        "bairro": "Centro",
        "cidade": "São Paulo",
        "uf": "SP",
        "cep": "01310-100",
    }
    base.update(alteracoes)
    return base


def mensagens(problemas):
    return {(p.campo, p.mensagem) for p in problemas}


def test_endereco_completo_e_consistente_nao_tem_problemas():
    assert validate_address(endereco()) == []


@pytest.mark.parametrize("campo", ["logradouro", "numero", "cidade", "uf", "cep"])
def test_campo_obrigatorio_ausente(campo):
    problemas = validate_address(endereco(**{campo: ""}))

    assert (campo, "campo obrigatório não encontrado") in mensagens(problemas)


def test_bairro_ausente_e_apontado():
    assert ("bairro", "bairro não encontrado") in mensagens(validate_address(endereco(bairro="")))


def test_complemento_e_opcional():
    assert validate_address(endereco(complemento="")) == []


@pytest.mark.parametrize("cep", ["1310-100", "013101-00", "01310100", "ABCDE-123"])
def test_cep_com_formato_invalido(cep):
    assert ("cep", "formato de CEP inválido") in mensagens(validate_address(endereco(cep=cep)))


def test_cep_zerado_e_invalido():
    assert ("cep", "CEP inválido") in mensagens(validate_address(endereco(cep="00000-000")))


def test_uf_inexistente():
    assert ("uf", "UF inexistente") in mensagens(validate_address(endereco(uf="XX")))


def test_cep_de_outra_uf_e_apontado():
    problemas = validate_address(endereco(cep="20040-020", uf="SP"))

    assert ("cep", "CEP não pertence à faixa de SP") in mensagens(problemas)


@pytest.mark.parametrize(
    "cep, uf",
    [("01310-100", "SP"), ("20040-020", "RJ"), ("30130-010", "MG"), ("80010-000", "PR"), ("70040-010", "DF")],
)
def test_faixa_de_cep_por_uf(cep, uf):
    assert uf_from_zip(cep) == uf


def test_numero_suspeito():
    assert ("numero", "número com formato suspeito") in mensagens(validate_address(endereco(numero="1O8X9")))


def test_numero_sem_numero_e_aceito():
    assert validate_address(endereco(numero="S/N")) == []


def test_cidade_com_digito_e_suspeita():
    assert ("cidade", "nome de cidade suspeito") in mensagens(validate_address(endereco(cidade="S4o Paulo")))


def test_termos_suspeitos_no_logradouro():
    problemas = validate_address(endereco(logradouro="Avenida Dom Pedro Tt"))

    assert ("logradouro", "termo suspeito: Tt") in mensagens(problemas)


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Rua XV de Novembro", []),
        ("Avenida Dom Pedro II", []),
        ("Rua Barão de kapetininga", ["kapetininga"]),
        ("Avenida Dom Pedro Tt", ["Tt"]),
        ("Bloco A", []),
        ("Rua 25 de Março", []),
    ],
)
def test_suspicious_words(texto, esperado):
    assert suspicious_words(texto) == esperado


def test_inferir_uf_a_partir_do_cep():
    assert infer_state({"uf": "", "cep": "09048-553"}) == "SP"
    assert infer_state({"uf": "SP", "cep": "09048-553"}) == ""
    assert infer_state({"uf": "", "cep": "invalido"}) == ""


def test_campos_a_revisar_seguem_a_ordem_do_endereco():
    problemas = validate_address(endereco(cep="", bairro="", numero=""))

    assert fields_to_review(problemas) == ["numero", "bairro", "cep"]
