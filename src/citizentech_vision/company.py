from dataclasses import dataclass

from .companies import EMPRESAS, REGIAO_CABECALHO
from .ocr import read_text
from .preprocess import crop_relative, prepare_for_ocr, to_gray
from .textmatch import fuzzy_contains

PONTUACAO_MINIMA = 0.4
MARGEM_MINIMA = 0.3


@dataclass(frozen=True)
class CompanyMatch:
    empresa: str
    confianca: float
    evidencias: tuple


def score_companies(texto):
    pontuacoes = {}
    for nome, config in EMPRESAS.items():
        total = 0.0
        achadas = []
        for palavra, peso in config.palavras_chave:
            if fuzzy_contains(texto, palavra):
                total += peso
                achadas.append(palavra)
        pontuacoes[nome] = (total, tuple(achadas))
    return pontuacoes


def identify_company_from_text(texto):
    pontuacoes = score_companies(texto)
    ordenadas = sorted(pontuacoes.items(), key=lambda item: item[1][0], reverse=True)
    melhor, (pontos, evidencias) = ordenadas[0]
    segundo = ordenadas[1][1][0]
    if pontos < PONTUACAO_MINIMA or pontos - segundo < MARGEM_MINIMA:
        return None
    return CompanyMatch(melhor, min(pontos, 1.0), evidencias)


def identify_company(pagina):
    cabecalho = crop_relative(pagina, REGIAO_CABECALHO)
    cinza = to_gray(cabecalho)
    tentativas = (
        lambda: cinza,
        lambda: prepare_for_ocr(cabecalho),
        lambda: 255 - cinza,
    )
    for preparar in tentativas:
        resultado = identify_company_from_text(read_text(preparar(), psm=6))
        if resultado is not None:
            return resultado
    return None
