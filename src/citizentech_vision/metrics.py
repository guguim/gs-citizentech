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
