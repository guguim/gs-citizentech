from citizentech_vision.textmatch import compact, fuzzy_contains, matches_any, tolerance_for


def test_compact_remove_acentos_espacos_e_pontuacao():
    assert compact("Endereço do  Imóvel:") == "ENDERECODOIMOVEL"


def test_tolerancia_cresce_com_o_tamanho():
    assert tolerance_for(4) == 0
    assert tolerance_for(6) == 1
    assert tolerance_for(12) == 2
    assert tolerance_for(20) == 3


def test_fuzzy_contains_acha_palavra_dentro_de_texto_maior():
    assert fuzzy_contains("Enel Distribuição São Paulo", "ENEL")
    assert fuzzy_contains("Sa besp 587481954864", "SABESP")


def test_fuzzy_contains_tolera_erros_de_ocr():
    assert fuzzy_contains("ENDERECO DO IMOVEI", "ENDERECODOIMOVEL")
    assert fuzzy_contains("Clero FATURA", "CLARO")


def test_fuzzy_contains_nao_tolera_palavra_curta_diferente():
    assert not fuzzy_contains("ENERGIA ELETRICA", "ENEL")


def test_fuzzy_contains_rejeita_texto_sem_relacao():
    assert not fuzzy_contains("CONTA DE LUZ", "SABESP")
    assert not fuzzy_contains("", "SABESP")


def test_matches_any():
    assert matches_any("AGENCIA DE ATENDIMENTO", ("SEDE", "ATENDIMENTO"))
    assert not matches_any("VILA INDUSTRIAL", ("SEDE", "ATENDIMENTO"))
