import unicodedata

import cv2
import numpy as np


def quad_iou(cantos_a, cantos_b):
    a = np.asarray(cantos_a, dtype=np.float32)
    b = np.asarray(cantos_b, dtype=np.float32)
    interseccao, _ = cv2.intersectConvexConvex(a, b)
    uniao = cv2.contourArea(a) + cv2.contourArea(b) - interseccao
    return float(interseccao / uniao) if uniao > 0 else 0.0


def max_corner_error(cantos_a, cantos_b):
    diferenca = np.asarray(cantos_a, dtype=np.float32) - np.asarray(cantos_b, dtype=np.float32)
    return float(np.linalg.norm(diferenca, axis=1).max())


def image_similarity(imagem_a, imagem_b):
    cinza_a = cv2.GaussianBlur(cv2.cvtColor(imagem_a, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    cinza_b = cv2.GaussianBlur(cv2.cvtColor(imagem_b, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    return float(cv2.matchTemplate(cinza_a, cinza_b, cv2.TM_CCOEFF_NORMED)[0][0])


def normalize_text(texto, sem_acentos=False):
    texto = unicodedata.normalize("NFC", texto).upper()
    if sem_acentos:
        decomposto = unicodedata.normalize("NFD", texto)
        texto = "".join(c for c in decomposto if unicodedata.category(c) != "Mn")
    return " ".join(texto.split())


def edit_distance(a, b):
    anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        atual = [i]
        for j, cb in enumerate(b, start=1):
            atual.append(min(anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + (ca != cb)))
        anterior = atual
    return anterior[-1]


def character_error_rate(referencia, hipotese, sem_acentos=False):
    ref = normalize_text(referencia, sem_acentos)
    hip = normalize_text(hipotese, sem_acentos)
    if not ref:
        return 0.0 if not hip else 1.0
    return edit_distance(ref, hip) / len(ref)


def word_error_rate(referencia, hipotese, sem_acentos=False):
    ref = normalize_text(referencia, sem_acentos).split()
    hip = normalize_text(hipotese, sem_acentos).split()
    if not ref:
        return 0.0 if not hip else 1.0
    return edit_distance(ref, hip) / len(ref)
