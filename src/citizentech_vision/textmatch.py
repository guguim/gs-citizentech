import re

from .metrics import normalize_text


def compact(texto):
    return re.sub(r"[^A-Z0-9]", "", normalize_text(texto, sem_acentos=True))


def tolerance_for(tamanho):
    if tamanho <= 4:
        return 0
    if tamanho <= 7:
        return 1
    if tamanho <= 14:
        return 2
    return 3


def min_substring_distance(texto, padrao):
    anterior = [0] * (len(texto) + 1)
    for i, cp in enumerate(padrao, start=1):
        atual = [i]
        for j, ct in enumerate(texto, start=1):
            atual.append(min(anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + (cp != ct)))
        anterior = atual
    return min(anterior)


def fuzzy_contains(texto, padrao, erros=None):
    texto = compact(texto)
    padrao = compact(padrao)
    if not padrao:
        return False
    if erros is None:
        erros = tolerance_for(len(padrao))
    return min_substring_distance(texto, padrao) <= erros


def matches_any(texto, padroes):
    return any(fuzzy_contains(texto, p) for p in padroes)
