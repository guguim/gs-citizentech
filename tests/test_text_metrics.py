import pytest

from citizentech_vision.metrics import (
    character_error_rate,
    edit_distance,
    normalize_text,
    word_error_rate,
)


def test_normalize_text_maiusculas_e_espacos():
    assert normalize_text("  Rua   das  Flores\n 10 ") == "RUA DAS FLORES 10"


def test_normalize_text_preserva_ou_remove_acentos():
    assert normalize_text("São Paulo") == "SÃO PAULO"
    assert normalize_text("São Paulo", sem_acentos=True) == "SAO PAULO"


def test_edit_distance_casos_basicos():
    assert edit_distance("", "") == 0
    assert edit_distance("abc", "abc") == 0
    assert edit_distance("abc", "") == 3
    assert edit_distance("kitten", "sitting") == 3


def test_edit_distance_funciona_com_listas_de_palavras():
    assert edit_distance(["a", "b", "c"], ["a", "x", "c"]) == 1


def test_cer_zero_para_textos_iguais_ignorando_caixa_e_espacos():
    assert character_error_rate("Rua A, 10", "RUA   A, 10") == 0.0


def test_cer_proporcional_aos_erros():
    assert character_error_rate("ABCDEFGHIJ", "ABCDEFGHIX") == pytest.approx(0.1)


def test_cer_sem_acentos_ignora_diferenca_de_acento():
    assert character_error_rate("SÃO PAULO", "SAO PAULO") > 0
    assert character_error_rate("SÃO PAULO", "SAO PAULO", sem_acentos=True) == 0.0


def test_cer_com_referencia_vazia():
    assert character_error_rate("", "") == 0.0
    assert character_error_rate("", "x") == 1.0


def test_wer_conta_palavras_erradas():
    assert word_error_rate("RUA DAS FLORES 10", "RUA DAS FLORAS 10") == pytest.approx(0.25)
    assert word_error_rate("A B", "A B") == 0.0
