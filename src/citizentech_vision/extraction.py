import re
from dataclasses import dataclass, field
from typing import NamedTuple

import numpy as np

from .address import ParsedAddress, attach_confidence, parse_address_lines
from .companies import EMPRESAS, ROTULOS_ENDERECO_CLIENTE, ROTULOS_OUTROS_ENDERECOS
from .company import identify_company, identify_company_from_text
from .document import DocumentDetection, rectify_document
from .ocr import group_lines, read_words
from .preprocess import apply_variant, crop_relative
from .textmatch import matches_any
from .validation import Problema, fields_to_review, infer_state, validate_address
from .voting import merge_candidates

METODO_AUTO = "auto"
METODO_ZONA = "zona"
METODO_ANCORA = "ancora"
METODOS = (METODO_AUTO, METODO_ZONA, METODO_ANCORA)

VARIANTE_PRINCIPAL = "mediana+adaptativo"
VARIANTES_REFORCO = ("mediana", "cinza")
LIMIAR_REVISAO = 0.8
LIMIAR_PALAVRA = 0.7
PENALIDADE_PROBLEMA = 0.15
MAX_LINHAS_ENDERECO = 4
LIMITE_SUPERIOR_ENDERECO = 0.45
FATOR_LACUNA_VERTICAL = 2.2
TOLERANCIA_COLUNA = 45
PADRAO_CEP_BUSCA = re.compile(r"(?<!\d)\d{5}\s*[-.:]?\s*\d{3}(?!\d)")


class Analise(NamedTuple):
    parsed: ParsedAddress
    linhas: list
    extras: list


@dataclass
class ExtractionResult:
    encontrado: bool
    empresa: str = None
    campos: dict = field(default_factory=dict)
    confianca: float = 0.0
    precisa_revisao: bool = True
    campos_revisar: list = field(default_factory=list)
    problemas: list = field(default_factory=list)
    metodo: str = "nenhum"
    reforco: bool = False
    linhas: list = field(default_factory=list)
    documento: DocumentDetection = None


def field_confidence(parsed):
    medias = [media for media, _ in parsed.conf_campo.values()]
    return float(np.mean(medias)) if medias else 0.0


def low_confidence_fields(parsed):
    return [c for c, (_, minima) in parsed.conf_campo.items() if minima < LIMIAR_PALAVRA]


def build_result(parsed, linhas, metodo, empresa, documento, extras=(), divergentes=(), reforco=False):
    campos = parsed.as_dict()
    inferida = infer_state(campos)
    if inferida:
        campos["uf"] = inferida
    problemas = list(validate_address(campos))
    problemas += [Problema(*a) for a in parsed.avisos]
    problemas += [Problema(*a) for a in extras]
    if inferida:
        problemas.append(Problema("uf", "UF inferida a partir do CEP"))
    if parsed.sem_virgula:
        problemas.append(Problema("numero", "vírgula ausente: separação do número incerta"))
    for campo in divergentes:
        problemas.append(Problema(campo, "leituras diferentes entre as variantes de pré-processamento"))
    for campo in low_confidence_fields(parsed):
        problemas.append(Problema(campo, "palavra com baixa confiança no OCR"))

    confianca = max(0.0, field_confidence(parsed) - PENALIDADE_PROBLEMA * len(problemas))
    encontrado = bool(parsed.logradouro and parsed.cep)
    return ExtractionResult(
        encontrado=encontrado,
        empresa=empresa,
        campos=campos,
        confianca=confianca,
        precisa_revisao=bool(problemas) or confianca < LIMIAR_REVISAO or not encontrado,
        campos_revisar=fields_to_review(problemas),
        problemas=[f"{p.campo}: {p.mensagem}" for p in problemas],
        metodo=metodo,
        reforco=reforco,
        linhas=[l.texto for l in linhas],
        documento=documento,
    )


def read_page_lines(imagem, variante, psm):
    return group_lines(read_words(apply_variant(imagem, variante), psm=psm))


def analyze_parsed(linhas, extras=()):
    parsed = parse_address_lines([l.texto for l in linhas])
    return Analise(attach_confidence(parsed, linhas), linhas, list(extras))


def zone_analysis(pagina, empresa, variante):
    recorte = crop_relative(pagina, EMPRESAS[empresa].zona_endereco)
    return analyze_parsed(read_page_lines(recorte, variante, psm=6))


def find_label_line(linhas):
    for indice, linha in enumerate(linhas):
        if matches_any(linha.texto, ROTULOS_ENDERECO_CLIENTE):
            return indice
    return None


def lines_below_label(linhas, indice):
    rotulo = linhas[indice]
    selecionadas = []
    anterior = rotulo
    for linha in linhas[indice + 1:]:
        if abs(linha.x0 - rotulo.x0) > TOLERANCIA_COLUNA:
            continue
        altura = max(anterior.y1 - anterior.y0, 1)
        if linha.y0 - anterior.y1 > FATOR_LACUNA_VERTICAL * altura:
            break
        if matches_any(linha.texto, ROTULOS_OUTROS_ENDERECOS) or find_label_line([linha]) is not None:
            break
        selecionadas.append(linha)
        anterior = linha
        if len(selecionadas) >= MAX_LINHAS_ENDERECO:
            break
    return selecionadas


def lines_above_zip(linhas, altura_pagina):
    for indice, linha in enumerate(linhas):
        if linha.y0 > LIMITE_SUPERIOR_ENDERECO * altura_pagina:
            break
        if not PADRAO_CEP_BUSCA.search(linha.texto):
            continue
        contexto = linhas[max(0, indice - MAX_LINHAS_ENDERECO):indice + 1]
        if any(matches_any(l.texto, ROTULOS_OUTROS_ENDERECOS) for l in contexto):
            continue
        inicio = indice
        while inicio > 0 and indice - inicio < MAX_LINHAS_ENDERECO - 1:
            atual, anterior = linhas[inicio], linhas[inicio - 1]
            altura = max(atual.y1 - atual.y0, 1)
            if atual.y0 - anterior.y1 > FATOR_LACUNA_VERTICAL * altura:
                break
            if abs(anterior.x0 - atual.x0) > TOLERANCIA_COLUNA:
                break
            inicio -= 1
        return linhas[inicio:indice + 1]
    return []


def anchor_analysis(pagina, variante):
    linhas = read_page_lines(pagina, variante, psm=3)
    indice = find_label_line(linhas)
    if indice is not None:
        return analyze_parsed(lines_below_label(linhas, indice)), linhas
    selecionadas = lines_above_zip(linhas, pagina.shape[0])
    extras = [("logradouro", "rótulo do endereço do cliente não encontrado")]
    return analyze_parsed(selecionadas, extras), linhas


def needs_reinforcement(resultado):
    return bool(resultado.problemas) or resultado.confianca < LIMIAR_REVISAO or not resultado.encontrado


def run_strategy(analisar, metodo, empresa, documento):
    primeira = analisar(VARIANTE_PRINCIPAL)
    resultado = build_result(primeira.parsed, primeira.linhas, metodo, empresa, documento, primeira.extras)
    if not needs_reinforcement(resultado):
        return resultado

    candidatos = [primeira] + [analisar(v) for v in VARIANTES_REFORCO]
    parsed, divergentes = merge_candidates([c.parsed for c in candidatos])
    return build_result(
        parsed, primeira.linhas, metodo, empresa, documento, primeira.extras, divergentes, reforco=True
    )


def extract_by_zone(pagina, empresa, documento):
    return run_strategy(lambda v: zone_analysis(pagina, empresa, v), METODO_ZONA, empresa, documento)


def extract_by_anchor(pagina, empresa, documento):
    cache = {}

    def analisar(variante):
        analise, linhas = anchor_analysis(pagina, variante)
        cache[variante] = linhas
        return analise

    if empresa is None:
        linhas = read_page_lines(pagina, VARIANTE_PRINCIPAL, psm=3)
        match = identify_company_from_text(" ".join(l.texto for l in linhas))
        empresa = match.empresa if match else None
    return run_strategy(analisar, METODO_ANCORA, empresa, documento)


def better_of(a, b):
    def chave(r):
        return (r.encontrado, not r.problemas, r.confianca)

    return a if chave(a) >= chave(b) else b


def extract_from_page(pagina, metodo=METODO_AUTO, documento=None):
    match = identify_company(pagina)
    empresa = match.empresa if match else None

    zona = None
    if metodo in (METODO_AUTO, METODO_ZONA) and empresa is not None:
        zona = extract_by_zone(pagina, empresa, documento)
        if metodo == METODO_ZONA or (zona.encontrado and not zona.precisa_revisao):
            return zona

    if metodo == METODO_ZONA:
        return ExtractionResult(encontrado=False, empresa=empresa, documento=documento)

    ancora = extract_by_anchor(pagina, empresa, documento)
    return better_of(zona, ancora) if zona is not None else ancora


def extract_address(foto, metodo=METODO_AUTO):
    retificado = rectify_document(foto)
    resultado = extract_from_page(retificado.imagem, metodo, retificado.deteccao)
    if not retificado.deteccao.encontrado:
        resultado.problemas.append("documento: página não detectada na foto")
        resultado.precisa_revisao = True
    return resultado
