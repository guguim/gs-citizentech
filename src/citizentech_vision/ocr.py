from dataclasses import dataclass

import pytesseract
from pytesseract import Output

from .ocr_setup import configure_tesseract

IDIOMA_PADRAO = "por"
PSM_PADRAO = 6
FATOR_LACUNA_COLUNA = 2.5


@dataclass(frozen=True)
class Palavra:
    texto: str
    x: int
    y: int
    largura: int
    altura: int
    confianca: float
    bloco: int
    paragrafo: int
    linha: int


@dataclass(frozen=True)
class Linha:
    texto: str
    palavras: tuple
    x0: int
    y0: int
    x1: int
    y1: int
    confianca: float


def read_text(imagem, idioma=IDIOMA_PADRAO, psm=PSM_PADRAO):
    configure_tesseract()
    return pytesseract.image_to_string(imagem, lang=idioma, config=f"--psm {psm}").strip()


def read_words(imagem, idioma=IDIOMA_PADRAO, psm=PSM_PADRAO):
    configure_tesseract()
    dados = pytesseract.image_to_data(
        imagem, lang=idioma, config=f"--psm {psm}", output_type=Output.DICT
    )
    palavras = []
    for i, texto in enumerate(dados["text"]):
        texto = texto.strip()
        confianca = float(dados["conf"][i])
        if not texto or confianca < 0:
            continue
        palavras.append(
            Palavra(
                texto=texto,
                x=int(dados["left"][i]),
                y=int(dados["top"][i]),
                largura=int(dados["width"][i]),
                altura=int(dados["height"][i]),
                confianca=confianca / 100.0,
                bloco=int(dados["block_num"][i]),
                paragrafo=int(dados["par_num"][i]),
                linha=int(dados["line_num"][i]),
            )
        )
    return palavras


def make_line(palavras):
    palavras = tuple(sorted(palavras, key=lambda p: p.x))
    return Linha(
        texto=" ".join(p.texto for p in palavras),
        palavras=palavras,
        x0=min(p.x for p in palavras),
        y0=min(p.y for p in palavras),
        x1=max(p.x + p.largura for p in palavras),
        y1=max(p.y + p.altura for p in palavras),
        confianca=sum(p.confianca for p in palavras) / len(palavras),
    )


def group_lines(palavras, fator_lacuna=FATOR_LACUNA_COLUNA):
    grupos = {}
    for palavra in palavras:
        grupos.setdefault((palavra.bloco, palavra.paragrafo, palavra.linha), []).append(palavra)

    linhas = []
    for grupo in grupos.values():
        grupo = sorted(grupo, key=lambda p: p.x)
        altura = sum(p.altura for p in grupo) / len(grupo)
        segmento = [grupo[0]]
        for palavra in grupo[1:]:
            anterior = segmento[-1]
            if palavra.x - (anterior.x + anterior.largura) > fator_lacuna * altura:
                linhas.append(make_line(segmento))
                segmento = []
            segmento.append(palavra)
        linhas.append(make_line(segmento))
    return sorted(linhas, key=lambda l: (l.y0, l.x0))
