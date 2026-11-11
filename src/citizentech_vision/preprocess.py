from functools import partial

import cv2
import numpy as np

ESCALA_PADRAO = 2.0
MEDIANA_PADRAO = 3
CONTRASTE_BAIXO = 100.0
PERCENTIL_BAIXO = 2
PERCENTIL_ALTO = 98
BLOCO_ADAPTATIVO = 51
CONSTANTE_ADAPTATIVA = 15
KERNEL_RUIDO = 3


def crop_relative(imagem, regiao):
    altura, largura = imagem.shape[:2]
    x0, y0, x1, y1 = regiao
    return imagem[
        int(round(y0 * altura)):int(round(y1 * altura)),
        int(round(x0 * largura)):int(round(x1 * largura)),
    ]


def to_gray(imagem):
    if imagem.ndim == 2:
        return imagem
    return cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)


def contrast_level(cinza):
    baixo, alto = np.percentile(to_gray(cinza), (PERCENTIL_BAIXO, PERCENTIL_ALTO))
    return float(alto - baixo)


def is_low_contrast(cinza, limiar=CONTRASTE_BAIXO):
    return contrast_level(cinza) < limiar


def upscale(imagem, escala=ESCALA_PADRAO):
    return cv2.resize(imagem, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)


def denoise_median(cinza, tamanho=MEDIANA_PADRAO):
    return cv2.medianBlur(to_gray(cinza), tamanho)


def equalize(cinza):
    return cv2.equalizeHist(to_gray(cinza))


def stretch_contrast(cinza):
    cinza = to_gray(cinza)
    baixo, alto = np.percentile(cinza, (PERCENTIL_BAIXO, PERCENTIL_ALTO))
    if alto - baixo < 1:
        return cinza
    alfa = 255.0 / (alto - baixo)
    return cv2.convertScaleAbs(cinza, alpha=alfa, beta=-baixo * alfa)


def stretch_if_low_contrast(cinza, limiar=CONTRASTE_BAIXO):
    cinza = to_gray(cinza)
    return stretch_contrast(cinza) if is_low_contrast(cinza, limiar) else cinza


def binarize_otsu(cinza):
    _, binaria = cv2.threshold(to_gray(cinza), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binaria


def binarize_adaptive(cinza, bloco=BLOCO_ADAPTATIVO, constante=CONSTANTE_ADAPTATIVA):
    return cv2.adaptiveThreshold(
        to_gray(cinza), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, bloco, constante
    )


def remove_specks(binaria, tamanho=KERNEL_RUIDO):
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (tamanho, tamanho))
    texto = cv2.bitwise_not(binaria)
    texto = cv2.morphologyEx(texto, cv2.MORPH_OPEN, kernel)
    return cv2.bitwise_not(texto)


def close_gaps(binaria, tamanho=KERNEL_RUIDO):
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (tamanho, tamanho))
    texto = cv2.bitwise_not(binaria)
    texto = cv2.morphologyEx(texto, cv2.MORPH_CLOSE, kernel)
    return cv2.bitwise_not(texto)


PASSOS = {
    "cinza": to_gray,
    "ampliar": upscale,
    "mediana": denoise_median,
    "mediana5": partial(denoise_median, tamanho=5),
    "equalizar": equalize,
    "esticar": stretch_contrast,
    "esticar_se_baixo": stretch_if_low_contrast,
    "otsu": binarize_otsu,
    "adaptativo": binarize_adaptive,
    "abertura": remove_specks,
    "fechamento": close_gaps,
}

VARIANTES = {
    "original": (),
    "cinza": ("cinza",),
    "ampliar": ("ampliar", "cinza"),
    "mediana": ("cinza", "mediana"),
    "mediana5": ("cinza", "mediana5"),
    "equalizar": ("cinza", "equalizar"),
    "esticar": ("cinza", "esticar"),
    "otsu": ("cinza", "otsu"),
    "mediana+otsu": ("cinza", "mediana", "otsu"),
    "equalizar+mediana+otsu": ("cinza", "equalizar", "mediana", "otsu"),
    "esticar+mediana+otsu": ("cinza", "esticar", "mediana", "otsu"),
    "mediana+adaptativo": ("cinza", "mediana", "adaptativo"),
    "ampliar+mediana+adaptativo": ("ampliar", "cinza", "mediana", "adaptativo"),
    "esticar+mediana+adaptativo": ("cinza", "esticar", "mediana", "adaptativo"),
    "esticar_se_baixo+mediana+adaptativo": ("cinza", "esticar_se_baixo", "mediana", "adaptativo"),
    "mediana+adaptativo+abertura": ("cinza", "mediana", "adaptativo", "abertura"),
    "mediana+adaptativo+fechamento": ("cinza", "mediana", "adaptativo", "fechamento"),
}


def preprocess(imagem, passos):
    resultado = imagem
    for nome in passos:
        resultado = PASSOS[nome](resultado)
    return resultado


def apply_variant(imagem, nome):
    return preprocess(imagem, VARIANTES[nome])


PIPELINE_OCR = "mediana+adaptativo"


def prepare_for_ocr(imagem):
    return apply_variant(imagem, PIPELINE_OCR)
