from dataclasses import dataclass
from typing import NamedTuple

import cv2
import numpy as np

DOCUMENT_SIZE = (1240, 1754)

EDGE_THRESHOLD = 3.0
SEARCH_WINDOWS = (40, 15)
SIDE_SAMPLES = 48
PEAK_RATIO = 0.3
MIN_PEAK = 3.0
SUPPORT_RATIO = 0.15
MIN_AREA_RATIO = 0.15
MAX_AREA_RATIO = 0.98
MIN_ASPECT = 1.1
MAX_ASPECT = 1.9
RELIABLE_CONFIDENCE = 0.6


@dataclass(frozen=True)
class DocumentDetection:
    encontrado: bool
    cantos: object
    confianca: float
    metodo: str

    @property
    def confiavel(self):
        return self.encontrado and self.confianca >= RELIABLE_CONFIDENCE


@dataclass(frozen=True)
class RectifiedDocument:
    imagem: np.ndarray
    deteccao: DocumentDetection


class Candidate(NamedTuple):
    pontuacao: float
    cantos: np.ndarray
    suporte: float


def order_corners(pontos):
    pontos = np.asarray(pontos, dtype=np.float32).reshape(4, 2)
    por_y = pontos[np.argsort(pontos[:, 1])]
    topo = por_y[:2][np.argsort(por_y[:2, 0])]
    base = por_y[2:][np.argsort(por_y[2:, 0])]
    return np.array([topo[0], topo[1], base[1], base[0]], dtype=np.float32)


def color_gradients(imagem):
    suave = cv2.GaussianBlur(imagem.astype(np.float32), (0, 0), 2)
    gx = cv2.Sobel(suave, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(suave, cv2.CV_32F, 0, 1, ksize=3) / 8
    return gx, gy


def gradient_mask(magnitude):
    bordas = (magnitude > EDGE_THRESHOLD).astype(np.uint8) * 255
    dilatada = cv2.dilate(bordas, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    return cv2.morphologyEx(dilatada, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)))


def otsu_mask(imagem):
    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    suave = cv2.GaussianBlur(cinza, (7, 7), 0)
    _, binaria = cv2.threshold(suave, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    fechada = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, kernel)
    return cv2.morphologyEx(fechada, cv2.MORPH_OPEN, kernel)


def quad_from_contour(contorno):
    casco = cv2.convexHull(contorno)
    perimetro = cv2.arcLength(casco, True)
    for fator in np.linspace(0.01, 0.1, 19):
        aproximado = cv2.approxPolyDP(casco, fator * perimetro, True)
        if len(aproximado) == 4:
            return aproximado.reshape(4, 2).astype(np.float32)
    return cv2.boxPoints(cv2.minAreaRect(casco)).astype(np.float32)


def sample_channels(campo, mapa_x, mapa_y):
    canais = [
        cv2.remap(campo[:, :, c], mapa_x, mapa_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        for c in range(campo.shape[2])
    ]
    return np.stack(canais, axis=-1)


def find_side_points(gx, gy, inicio, fim, centro, janela):
    direcao = fim - inicio
    unitario = direcao / np.linalg.norm(direcao)
    normal = np.array([-unitario[1], unitario[0]], dtype=np.float32)
    if np.dot(normal, (inicio + fim) / 2 - centro) < 0:
        normal = -normal

    posicoes = np.linspace(0.12, 0.88, SIDE_SAMPLES, dtype=np.float32)
    base = inicio + np.outer(posicoes, direcao)
    deslocamentos = np.arange(-janela, janela + 1, dtype=np.float32)
    pontos = base[:, None, :] + deslocamentos[None, :, None] * normal
    mapa_x = pontos[..., 0].astype(np.float32)
    mapa_y = pontos[..., 1].astype(np.float32)

    gxp = sample_channels(gx, mapa_x, mapa_y)
    gyp = sample_channels(gy, mapa_x, mapa_y)
    perfil = np.sqrt(((gxp * normal[0] + gyp * normal[1]) ** 2).sum(axis=2))

    escolhidos = np.zeros(len(posicoes), dtype=int)
    forcas = np.zeros(len(posicoes))
    for i, linha in enumerate(perfil):
        limiar = max(PEAK_RATIO * linha.max(), MIN_PEAK)
        picos = [
            j
            for j in range(1, len(linha) - 1)
            if linha[j] >= limiar and linha[j] >= linha[j - 1] and linha[j] >= linha[j + 1]
        ]
        escolhidos[i] = max(picos) if picos else int(linha.argmax())
        forcas[i] = linha[escolhidos[i]]
    return base + deslocamentos[escolhidos][:, None] * normal, forcas


def fit_line(pontos):
    mediana = np.median(pontos, axis=0)
    distancias = np.linalg.norm(pontos - mediana, axis=1)
    mantidos = pontos[distancias <= np.percentile(distancias, 85) + 1e-6]
    vx, vy, x0, y0 = cv2.fitLine(mantidos.astype(np.float32), cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
    return np.array([x0, y0], dtype=np.float32), np.array([vx, vy], dtype=np.float32)


def intersect_lines(reta_a, reta_b):
    ponto_a, direcao_a = reta_a
    ponto_b, direcao_b = reta_b
    sistema = np.array([direcao_a, -direcao_b]).T
    if abs(np.linalg.det(sistema)) < 1e-6:
        return None
    t = np.linalg.solve(sistema, ponto_b - ponto_a)
    return ponto_a + t[0] * direcao_a


def refine_quad(gx, gy, cantos, janela):
    centro = cantos.mean(axis=0)
    retas, forcas = [], []
    for i in range(4):
        pontos, forca = find_side_points(gx, gy, cantos[i], cantos[(i + 1) % 4], centro, janela)
        retas.append(fit_line(pontos))
        forcas.append(np.median(forca))

    novos = [intersect_lines(retas[i - 1], retas[i]) for i in range(4)]
    if any(canto is None for canto in novos):
        return cantos, np.zeros(4)
    return np.array(novos, dtype=np.float32), np.array(forcas)


def is_valid_quad(cantos, forma):
    altura, largura = forma[:2]
    proporcao_area = cv2.contourArea(cantos) / (altura * largura)
    topo = np.linalg.norm(cantos[1] - cantos[0])
    base = np.linalg.norm(cantos[2] - cantos[3])
    esquerda = np.linalg.norm(cantos[3] - cantos[0])
    direita = np.linalg.norm(cantos[2] - cantos[1])
    aspecto = ((esquerda + direita) / 2) / ((topo + base) / 2)
    dentro = np.all(
        (cantos[:, 0] > -20) & (cantos[:, 0] < largura + 20) & (cantos[:, 1] > -20) & (cantos[:, 1] < altura + 20)
    )
    return (
        MIN_AREA_RATIO <= proporcao_area <= MAX_AREA_RATIO
        and MIN_ASPECT <= aspecto <= MAX_ASPECT
        and bool(dentro)
        and cv2.isContourConvex(cantos.reshape(-1, 1, 2))
    )


def candidates_from_mask(mascara, gx, gy, referencia, forma):
    area_imagem = forma[0] * forma[1]
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidatos = []
    for contorno in sorted(contornos, key=cv2.contourArea, reverse=True)[:2]:
        cantos = quad_from_contour(contorno)
        if cv2.contourArea(cantos) / area_imagem < MIN_AREA_RATIO:
            continue
        cantos = order_corners(cantos)
        for janela in SEARCH_WINDOWS:
            cantos, forcas = refine_quad(gx, gy, cantos, janela)
        if not is_valid_quad(cantos, forma):
            continue
        suporte = float(np.mean(np.minimum(forcas / (SUPPORT_RATIO * referencia), 1.0)))
        pontuacao = suporte * cv2.contourArea(cantos) / area_imagem
        candidatos.append(Candidate(pontuacao, cantos, suporte))
    return candidatos


def detect_document(imagem):
    gx, gy = color_gradients(imagem)
    magnitude = np.sqrt((gx**2 + gy**2).sum(axis=2))
    referencia = float(np.percentile(magnitude, 99))
    if referencia <= 0:
        return DocumentDetection(False, None, 0.0, "nenhum")

    metodos = (
        ("gradiente", lambda: gradient_mask(magnitude)),
        ("otsu", lambda: otsu_mask(imagem)),
    )
    for nome, gerar_mascara in metodos:
        candidatos = candidates_from_mask(gerar_mascara(), gx, gy, referencia, imagem.shape)
        if candidatos:
            melhor = max(candidatos, key=lambda c: c.pontuacao)
            return DocumentDetection(True, melhor.cantos, round(melhor.suporte, 3), nome)
    return DocumentDetection(False, None, 0.0, "nenhum")


def warp_document(imagem, cantos, tamanho=DOCUMENT_SIZE):
    largura, altura = tamanho
    destino = np.array([[0, 0], [largura - 1, 0], [largura - 1, altura - 1], [0, altura - 1]], dtype=np.float32)
    matriz = cv2.getPerspectiveTransform(np.asarray(cantos, dtype=np.float32), destino)
    return cv2.warpPerspective(imagem, matriz, tamanho, flags=cv2.INTER_CUBIC)


def rectify_document(imagem, tamanho=DOCUMENT_SIZE):
    deteccao = detect_document(imagem)
    if not deteccao.encontrado:
        return RectifiedDocument(imagem, deteccao)
    return RectifiedDocument(warp_document(imagem, deteccao.cantos, tamanho), deteccao)
