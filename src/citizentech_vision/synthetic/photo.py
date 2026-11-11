import random
from dataclasses import dataclass

import cv2
import numpy as np

CANVAS_SIZE = (1300, 1800)

BACKGROUND_COLORS = {
    "madeira": (60, 95, 140),
    "escuro": (48, 48, 52),
    "azul": (150, 105, 70),
    "claro": (205, 212, 218),
}

CONDITIONS = {
    "frontal": {
        "perspectiva": (0.01, 0.025),
        "rotacao": (-2.0, 2.0),
        "brilho": (0.95, 1.05),
        "sombra": (0.0, 0.0),
        "desfoque": 0,
        "ruido": 2.0,
        "fundos": ("madeira", "escuro"),
        "jpeg": 90,
    },
    "inclinada": {
        "perspectiva": (0.05, 0.09),
        "rotacao": (-8.0, 8.0),
        "brilho": (0.85, 0.95),
        "sombra": (0.1, 0.25),
        "desfoque": 3,
        "ruido": 4.0,
        "fundos": ("madeira", "escuro", "azul"),
        "jpeg": 85,
    },
    "dificil": {
        "perspectiva": (0.09, 0.14),
        "rotacao": (-15.0, 15.0),
        "brilho": (0.6, 0.75),
        "sombra": (0.3, 0.5),
        "desfoque": 5,
        "ruido": 8.0,
        "fundos": ("azul", "claro", "madeira"),
        "jpeg": 75,
    },
}


@dataclass(frozen=True)
class PhotoParams:
    condicao: str
    perspectiva: float
    rotacao_graus: float
    brilho: float
    sombra: float
    desfoque: int
    ruido: float
    fundo: str
    qualidade_jpeg: int


def sample_params(condicao, rng):
    faixa = CONDITIONS[condicao]
    return PhotoParams(
        condicao=condicao,
        perspectiva=round(rng.uniform(*faixa["perspectiva"]), 3),
        rotacao_graus=round(rng.uniform(*faixa["rotacao"]), 2),
        brilho=round(rng.uniform(*faixa["brilho"]), 3),
        sombra=round(rng.uniform(*faixa["sombra"]), 3),
        desfoque=faixa["desfoque"],
        ruido=faixa["ruido"],
        fundo=rng.choice(faixa["fundos"]),
        qualidade_jpeg=faixa["jpeg"],
    )


def make_background(tamanho_canvas, tipo, rng):
    largura, altura = tamanho_canvas
    gerador = np.random.default_rng(rng.randrange(2**32))
    fundo = np.tile(np.array(BACKGROUND_COLORS[tipo], dtype=np.float32), (altura, largura, 1))
    if tipo == "madeira":
        y = np.arange(altura, dtype=np.float32)[:, None, None]
        fase_a, fase_b = gerador.uniform(0, 6.28, 2)
        fundo += 12 * np.sin(y * 0.04 + fase_a) + 6 * np.sin(y * 0.11 + fase_b)
    fundo += gerador.normal(0, 4, (altura, largura, 1))
    return np.clip(fundo, 0, 255)


def sample_corners(forma_documento, tamanho_canvas, params, rng):
    doc_altura, doc_largura = forma_documento[:2]
    largura_canvas, altura_canvas = tamanho_canvas
    largura = rng.uniform(0.72, 0.80) * largura_canvas
    altura = largura * doc_altura / doc_largura
    centro = np.array(
        [
            largura_canvas / 2 + rng.uniform(-0.03, 0.03) * largura_canvas,
            altura_canvas / 2 + rng.uniform(-0.03, 0.03) * altura_canvas,
        ]
    )
    base = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]]) * np.array([largura / 2, altura / 2])
    deslocamento = np.array(
        [
            [
                rng.uniform(-1, 1) * params.perspectiva * largura,
                rng.uniform(-1, 1) * params.perspectiva * altura * 0.6,
            ]
            for _ in range(4)
        ]
    )
    angulo = np.deg2rad(params.rotacao_graus)
    rotacao = np.array([[np.cos(angulo), -np.sin(angulo)], [np.sin(angulo), np.cos(angulo)]])
    cantos = (base + deslocamento) @ rotacao.T + centro

    margem = 12
    for _ in range(60):
        dentro = (
            cantos[:, 0].min() >= margem
            and cantos[:, 0].max() <= largura_canvas - margem
            and cantos[:, 1].min() >= margem
            and cantos[:, 1].max() <= altura_canvas - margem
        )
        if dentro:
            break
        cantos = (cantos - centro) * 0.96 + centro
    return cantos.astype(np.float32)


def light_gradient(tamanho_canvas, intensidade, rng):
    largura, altura = tamanho_canvas
    if intensidade == 0:
        return np.ones((altura, largura), dtype=np.float32)
    angulo = rng.uniform(0, 2 * np.pi)
    x, y = np.meshgrid(np.linspace(0, 1, largura), np.linspace(0, 1, altura))
    rampa = x * np.cos(angulo) + y * np.sin(angulo)
    rampa = (rampa - rampa.min()) / (rampa.max() - rampa.min())
    return (1 - intensidade * rampa).astype(np.float32)


def shadow_band(tamanho_canvas, rng):
    largura, altura = tamanho_canvas
    topo = rng.uniform(0.2, 0.6) * altura
    desvio = rng.uniform(-300, 300)
    espessura = rng.uniform(250, 450)
    pontos = np.array(
        [[0, topo], [largura, topo + desvio], [largura, topo + desvio + espessura], [0, topo + espessura]],
        dtype=np.int32,
    )
    mascara = np.zeros((altura, largura), dtype=np.float32)
    cv2.fillConvexPoly(mascara, pontos, 1.0)
    mascara = cv2.GaussianBlur(mascara, (0, 0), 45)
    return 1 - 0.4 * mascara


def render_photo(documento_bgr, params, rng, tamanho_canvas=CANVAS_SIZE):
    cantos = sample_corners(documento_bgr.shape, tamanho_canvas, params, rng)

    escala = min(1.0, float(np.linalg.norm(cantos[1] - cantos[0])) / documento_bgr.shape[1])
    reduzido = cv2.resize(documento_bgr, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
    altura_r, largura_r = reduzido.shape[:2]
    origem = np.array([[0, 0], [largura_r, 0], [largura_r, altura_r], [0, altura_r]], dtype=np.float32)

    matriz = cv2.getPerspectiveTransform(origem, cantos)
    pagina = cv2.warpPerspective(reduzido, matriz, tamanho_canvas, flags=cv2.INTER_LINEAR)
    mascara = cv2.warpPerspective(
        np.full((altura_r, largura_r), 255, dtype=np.uint8), matriz, tamanho_canvas, flags=cv2.INTER_LINEAR
    )
    alfa = (mascara.astype(np.float32) / 255)[:, :, None]

    fundo = make_background(tamanho_canvas, params.fundo, rng)
    sombra_projetada = cv2.GaussianBlur(mascara, (0, 0), 18).astype(np.float32) / 255
    sombra_projetada = np.roll(sombra_projetada, (14, 14), axis=(0, 1))
    fundo = fundo * (1 - 0.35 * sombra_projetada[:, :, None])

    foto = fundo * (1 - alfa) + pagina.astype(np.float32) * alfa
    foto *= light_gradient(tamanho_canvas, params.sombra, rng)[:, :, None]
    if params.condicao == "dificil":
        foto *= shadow_band(tamanho_canvas, rng)[:, :, None]
    foto *= params.brilho

    if params.desfoque:
        foto = cv2.GaussianBlur(foto, (params.desfoque, params.desfoque), 0)

    gerador = np.random.default_rng(rng.randrange(2**32))
    foto += gerador.normal(0, params.ruido, foto.shape)
    return np.clip(foto, 0, 255).astype(np.uint8), cantos
