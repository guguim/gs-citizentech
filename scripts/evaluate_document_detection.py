import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from citizentech_vision.document import order_corners, rectify_document
from citizentech_vision.metrics import image_similarity, max_corner_error, quad_iou

DADOS = RAIZ / "data"
SAIDA = DADOS / "output" / "rectified"
LIMIAR_IOU = 0.95


def avaliar(entrada):
    foto = cv2.imread(str(DADOS / entrada["foto"]))
    limpo = cv2.imread(str(DADOS / entrada["documento_limpo"]))

    inicio = time.perf_counter()
    resultado = rectify_document(foto, tamanho=(limpo.shape[1], limpo.shape[0]))
    tempo = time.perf_counter() - inicio

    cv2.imwrite(str(SAIDA / f"{entrada['id']}.png"), resultado.imagem)

    if not resultado.deteccao.encontrado:
        return {"encontrado": False, "iou": 0.0, "erro": float("nan"), "similaridade": 0.0, "tempo": tempo}

    reais = order_corners(np.array(entrada["cantos_documento_foto"], dtype=np.float32))
    return {
        "encontrado": True,
        "iou": quad_iou(resultado.deteccao.cantos, reais),
        "erro": max_corner_error(resultado.deteccao.cantos, reais),
        "similaridade": image_similarity(resultado.imagem, limpo),
        "tempo": tempo,
    }


def resumir(titulo, grupos):
    print(f"\n{titulo}")
    print(f"{'grupo':12s} {'fotos':>5s} {'achou':>6s} {'IoU>=0.95':>10s} {'IoU medio':>10s} {'erro canto (px)':>16s} {'similaridade':>13s}")
    for nome, itens in grupos.items():
        total = len(itens)
        print(
            f"{nome:12s} {total:5d} "
            f"{sum(i['encontrado'] for i in itens):6d} "
            f"{sum(i['iou'] >= LIMIAR_IOU for i in itens):10d} "
            f"{np.mean([i['iou'] for i in itens]):10.4f} "
            f"{np.nanmean([i['erro'] for i in itens]):16.1f} "
            f"{np.mean([i['similaridade'] for i in itens]):13.4f}"
        )


def main():
    gabarito = json.loads((DADOS / "ground_truth" / "ground_truth.json").read_text(encoding="utf-8"))
    SAIDA.mkdir(parents=True, exist_ok=True)

    por_condicao, por_empresa, todos = defaultdict(list), defaultdict(list), []
    for entrada in gabarito:
        resultado = avaliar(entrada)
        resultado["id"] = entrada["id"]
        por_condicao[entrada["condicao"]].append(resultado)
        por_empresa[entrada["empresa"]].append(resultado)
        todos.append(resultado)

    resumir("Por condição", por_condicao)
    resumir("Por empresa", por_empresa)
    resumir("Geral", {"todas": todos})
    print(f"\nTempo médio por foto: {np.mean([r['tempo'] for r in todos]):.2f} s")

    falhas = [r["id"] for r in todos if r["iou"] < LIMIAR_IOU]
    print(f"Fotos abaixo de IoU {LIMIAR_IOU}: {', '.join(falhas) if falhas else 'nenhuma'}")
    print(f"Imagens corrigidas salvas em {SAIDA}")


if __name__ == "__main__":
    main()
