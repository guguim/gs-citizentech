import argparse
import json
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from citizentech_vision.address import CAMPOS
from citizentech_vision.companies import ALTURA, EMPRESAS, LARGURA
from citizentech_vision.document import detect_document, rectify_document, warp_document
from citizentech_vision.extraction import extract_address
from citizentech_vision.preprocess import (
    PERCENTIL_ALTO,
    PERCENTIL_BAIXO,
    binarize_adaptive,
    contrast_level,
    crop_relative,
    denoise_median,
    to_gray,
)
from evaluate_extraction import avaliar

DADOS = RAIZ / "data"
SAIDA_PADRAO = RAIZ / "docs" / "figures"
CONDICOES = ("frontal", "inclinada", "dificil")
NOMES_CONDICAO = {"frontal": "Frontal", "inclinada": "Inclinada", "dificil": "Difícil"}
NOMES_EMPRESA = {"enel": "Enel", "sabesp": "Sabesp", "claro": "Claro"}
NOMES_CAMPO = {
    "logradouro": "logradouro",
    "numero": "número",
    "complemento": "complemento",
    "bairro": "bairro",
    "cidade": "cidade",
    "uf": "UF",
    "cep": "CEP",
}

TINTA = "#1a1a19"
TINTA_SUAVE = "#52514e"
GRADE = "#d9d8d3"
SUPERFICIE = "#ffffff"
AZUL = "#2a78d6"
LARANJA = "#eb6834"
AQUA = "#1baf7a"
VERDE_OK = "#1b6e3b"
VERMELHO = "#b3261e"
CORES_EMPRESA = {"enel": AZUL, "sabesp": LARANJA, "claro": AQUA}

EXEMPLOS_DETECCAO = ("enel_01_frontal", "sabesp_02_inclinada", "claro_03_dificil")
EXEMPLOS_PRE = ("sabesp_01_frontal", "claro_03_dificil")
EXEMPLOS_EXTRACAO = ("enel_02_inclinada", "sabesp_01_inclinada", "claro_02_inclinada")

plt.rcParams.update(
    {
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "savefig.facecolor": SUPERFICIE,
        "text.color": TINTA,
        "axes.labelcolor": TINTA_SUAVE,
        "xtick.color": TINTA_SUAVE,
        "ytick.color": TINTA_SUAVE,
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def carregar_gabarito():
    caminho = DADOS / "ground_truth" / "ground_truth.json"
    return {e["id"]: e for e in json.loads(caminho.read_text(encoding="utf-8"))}


def ler_foto(entrada):
    return cv2.imread(str(DADOS / entrada["foto"]))


def rgb(imagem):
    if imagem.ndim == 2:
        return imagem
    return cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)


def mostrar(ax, imagem):
    ax.imshow(rgb(imagem), cmap="gray", vmin=0, vmax=255)
    ax.set_xticks([])
    ax.set_yticks([])
    for lado in ax.spines.values():
        lado.set_visible(True)
        lado.set_color(GRADE)


def salvar(fig, destino, nome):
    caminho = destino / nome
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"gerado {caminho.relative_to(RAIZ)}")


def figura_deteccao(gabarito, destino):
    fig, eixos = plt.subplots(len(EXEMPLOS_DETECCAO), 3, figsize=(8.6, 3.95 * len(EXEMPLOS_DETECCAO)))
    titulos = ("1. Foto original", "2. Documento detectado", "3. Perspectiva corrigida")
    for linha, id_ in enumerate(EXEMPLOS_DETECCAO):
        entrada = gabarito[id_]
        foto = ler_foto(entrada)
        deteccao = detect_document(foto)
        cantos = np.asarray(deteccao.cantos, dtype=float)
        pagina = warp_document(foto, deteccao.cantos)

        mostrar(eixos[linha, 0], foto)
        mostrar(eixos[linha, 1], foto)
        fechado = np.vstack([cantos, cantos[:1]])
        eixos[linha, 1].plot(fechado[:, 0], fechado[:, 1], color=AQUA, linewidth=2.2)
        eixos[linha, 1].scatter(cantos[:, 0], cantos[:, 1], s=30, color=LARANJA, edgecolor="white", linewidth=1.2, zorder=3)
        for numero, (x, y) in enumerate(cantos, start=1):
            eixos[linha, 1].annotate(str(numero), (x, y), xytext=(7, -7), textcoords="offset points", color=TINTA, fontsize=7.5, fontweight="bold", bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
        mostrar(eixos[linha, 2], pagina)

        rotulo = f"{NOMES_EMPRESA[entrada['empresa']]} · {NOMES_CONDICAO[entrada['condicao']]}\nconfiança da detecção: {deteccao.confianca:.2f}"
        eixos[linha, 0].set_ylabel(rotulo, rotation=90, labelpad=8, fontsize=8.5, color=TINTA_SUAVE)
        if linha == 0:
            for coluna, titulo in enumerate(titulos):
                eixos[linha, coluna].set_title(titulo, fontsize=9.5, fontweight="bold", loc="left", pad=8)
    fig.tight_layout(h_pad=1.2, w_pad=0.8)
    salvar(fig, destino, "01_deteccao_e_perspectiva.png")


def figura_preprocessamento(gabarito, destino):
    blocos = []
    for id_ in EXEMPLOS_PRE:
        entrada = gabarito[id_]
        pagina = rectify_document(ler_foto(entrada)).imagem
        roi = crop_relative(pagina, entrada["regiao_endereco"])
        cinza = to_gray(roi)
        mediana = denoise_median(cinza)
        binaria = binarize_adaptive(mediana)
        blocos.append((entrada, roi, cinza, mediana, binaria))

    razoes = []
    for indice, (_, roi, *_) in enumerate(blocos):
        if indice:
            razoes.append(0.1)
        razoes.extend([roi.shape[0] / roi.shape[1]] * 4 + [0.32])
    largura = 7.6
    fig = plt.figure(figsize=(largura, 5.4 * sum(razoes) * 1.12 + 0.9))
    grade = fig.add_gridspec(len(razoes), 1, height_ratios=razoes, hspace=0.22, left=0.27, right=0.98, top=0.975, bottom=0.05)

    passos = ("Recorte do endereço (ROI)", "Tons de cinza", "Filtro de mediana 3×3", "Limiar adaptativo (resultado)")
    for indice, (entrada, roi, cinza, mediana, binaria) in enumerate(blocos):
        base = indice * 6
        imagens = (roi, cinza, mediana, binaria)
        for deslocamento, (imagem, passo) in enumerate(zip(imagens, passos)):
            ax = fig.add_subplot(grade[base + deslocamento])
            mostrar(ax, imagem)
            ax.set_ylabel(passo, rotation=0, ha="right", va="center", labelpad=10, fontsize=9, color=TINTA_SUAVE)
            if deslocamento == 0:
                ax.set_title(f"{NOMES_EMPRESA[entrada['empresa']]} · {NOMES_CONDICAO[entrada['condicao']]}", loc="left", fontsize=11, fontweight="bold", pad=6)

        ax = fig.add_subplot(grade[base + 4])
        baixo, alto = np.percentile(cinza, (PERCENTIL_BAIXO, PERCENTIL_ALTO))
        ax.hist(cinza.ravel(), bins=64, range=(0, 256), color=TINTA_SUAVE, linewidth=0)
        ax.axvline(baixo, color=LARANJA, linewidth=1.6)
        ax.axvline(alto, color=AZUL, linewidth=1.6)
        ax.set_xlim(0, 255)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        ax.set_xlabel(f"Histograma da ROI em cinza. Contraste (p{PERCENTIL_ALTO} − p{PERCENTIL_BAIXO}) = {contrast_level(cinza):.0f}", fontsize=9, loc="left")
        ax.set_ylabel("Histograma", rotation=0, ha="right", va="center", labelpad=10, fontsize=9, color=TINTA_SUAVE)
        ax.text(baixo, ax.get_ylim()[1] * 0.92, f" p{PERCENTIL_BAIXO}", color=LARANJA, fontsize=8.5, va="top", ha="left")
        ax.text(alto, ax.get_ylim()[1] * 0.92, f"p{PERCENTIL_ALTO} ", color=AZUL, fontsize=8.5, va="top", ha="right")
    salvar(fig, destino, "02_preprocessamento_antes_e_depois.png")


def linhas_do_painel(entrada, resultado):
    esperado = entrada["endereco"]
    linhas = []
    for campo in CAMPOS:
        obtido = resultado.campos.get(campo, "")
        ok = obtido.strip().lower() == esperado[campo].strip().lower()
        marca = "✓" if ok else "✗"
        linhas.append((marca, ok, f"{NOMES_CAMPO[campo]:<12s}{obtido or '—'}", None if ok else f"esperado: {esperado[campo]}"))
    return linhas


def figura_extracao(gabarito, destino):
    fig = plt.figure(figsize=(7.4, 3.6 * len(EXEMPLOS_EXTRACAO)))
    grade = fig.add_gridspec(len(EXEMPLOS_EXTRACAO), 2, width_ratios=(0.8, 1.75), wspace=0.04, hspace=0.16)
    for linha, id_ in enumerate(EXEMPLOS_EXTRACAO):
        entrada = gabarito[id_]
        foto = ler_foto(entrada)
        pagina = rectify_document(foto).imagem
        resultado = extract_address(foto)
        empresa = entrada["empresa"]

        ax = fig.add_subplot(grade[linha, 0])
        mostrar(ax, pagina)
        x0, y0, x1, y1 = EMPRESAS[empresa].zona_endereco
        ax.add_patch(Rectangle((x0 * LARGURA, y0 * ALTURA), (x1 - x0) * LARGURA, (y1 - y0) * ALTURA, fill=False, edgecolor=AQUA, linewidth=2.6))
        ax.text(x0 * LARGURA + 8, y1 * ALTURA + 12, "zona lida", color=VERDE_OK, fontsize=6.5, fontweight="bold", va="top", bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
        ax.set_title(f"{NOMES_EMPRESA[empresa]} · {NOMES_CONDICAO[entrada['condicao']]}", loc="left", fontsize=9.5, fontweight="bold", pad=5)

        painel = fig.add_subplot(grade[linha, 1])
        painel.axis("off")
        painel.set_xlim(0, 1)
        painel.set_ylim(0, 1)
        identificada = NOMES_EMPRESA.get(resultado.empresa, "não identificada")
        painel.text(0, 0.99, "Resultado da extração", fontsize=9.5, fontweight="bold", va="top")
        painel.text(0, 0.925, f"empresa identificada: {identificada} · método: {resultado.metodo} · confiança: {resultado.confianca:.2f}", fontsize=7.6, color=TINTA_SUAVE, va="top")
        y = 0.84
        for marca, ok, lido, esperado_txt in linhas_do_painel(entrada, resultado):
            painel.text(0, y, marca, fontsize=8.5, color=VERDE_OK if ok else VERMELHO, va="top", fontweight="bold")
            painel.text(0.045, y, lido, fontsize=8, family="DejaVu Sans Mono", va="top")
            if esperado_txt:
                painel.text(0.045, y - 0.045, esperado_txt, fontsize=7.2, color=VERMELHO, va="top", family="DejaVu Sans Mono")
                y -= 0.045
            y -= 0.062
        revisar = ", ".join(NOMES_CAMPO[c] for c in resultado.campos_revisar) or "nenhum"
        painel.text(0, y - 0.01, f"campos marcados para revisão: {revisar}", fontsize=7.6, color=TINTA_SUAVE, va="top")
        y -= 0.09
        painel.text(0, y, "Outros endereços da fatura, ignorados:", fontsize=8.2, fontweight="bold", va="top")
        y -= 0.06
        for distrator in entrada["enderecos_distratores"]:
            for parte in textwrap.wrap(distrator, 82):
                painel.text(0.02, y, f"· {parte}" if parte == textwrap.wrap(distrator, 82)[0] else f"  {parte}", fontsize=7.2, color=TINTA_SUAVE, va="top")
                y -= 0.045
            y -= 0.015
    salvar(fig, destino, "03_extracao_do_endereco_do_cliente.png")


def percentual(valores):
    return 100.0 * float(np.mean(valores))


def rotular_barras(ax, barras, formato, deslocamento=2):
    for barra in barras:
        altura = barra.get_height()
        ax.annotate(formato(altura), (barra.get_x() + barra.get_width() / 2, altura), xytext=(0, deslocamento), textcoords="offset points", ha="center", va="bottom", fontsize=8.5, color=TINTA)


def figura_metricas(resultados, destino):
    por_empresa_condicao = defaultdict(list)
    por_condicao = defaultdict(list)
    for r in resultados:
        por_empresa_condicao[(r["empresa"], r["condicao"])].append(r)
        por_condicao[r["condicao"]].append(r)

    fig = plt.figure(figsize=(7.4, 6.2))
    grade = fig.add_gridspec(2, 2, height_ratios=(1.15, 1), hspace=0.42, wspace=0.42)
    ax_a = fig.add_subplot(grade[0, :])
    ax_b = fig.add_subplot(grade[1, 0])
    ax_c = fig.add_subplot(grade[1, 1])

    largura = 0.26
    posicoes = np.arange(len(CONDICOES))
    for indice, empresa in enumerate(("enel", "sabesp", "claro")):
        valores = [percentual([r["tudo"] for r in por_empresa_condicao[(empresa, c)]]) for c in CONDICOES]
        barras = ax_a.bar(posicoes + (indice - 1) * (largura + 0.02), valores, largura, color=CORES_EMPRESA[empresa], label=NOMES_EMPRESA[empresa], linewidth=0)
        rotular_barras(ax_a, barras, lambda v: f"{v:.0f}")
    ax_a.set_xticks(posicoes, [NOMES_CONDICAO[c] for c in CONDICOES])
    ax_a.set_ylim(0, 115)
    ax_a.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax_a.yaxis.grid(True, color=GRADE, linewidth=0.8)
    ax_a.set_axisbelow(True)
    ax_a.set_title("Endereço completo correto, por condição da foto", loc="left", fontsize=10.5, fontweight="bold")
    ax_a.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=9, handlelength=1.2)

    campos_ordenados = sorted(CAMPOS, key=lambda c: percentual([r["campos"][c] for r in resultados]))
    valores_campo = [percentual([r["campos"][c] for r in resultados]) for c in campos_ordenados]
    barras = ax_b.barh([NOMES_CAMPO[c] for c in campos_ordenados], valores_campo, height=0.55, color=AZUL, linewidth=0)
    for barra, valor in zip(barras, valores_campo):
        ax_b.annotate(f"{valor:.0f}%", (valor, barra.get_y() + barra.get_height() / 2), xytext=(4, 0), textcoords="offset points", va="center", fontsize=8.5, color=TINTA)
    ax_b.set_xlim(0, 112)
    ax_b.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax_b.xaxis.grid(True, color=GRADE, linewidth=0.8)
    ax_b.set_axisbelow(True)
    ax_b.set_title("Acerto por campo (36 fotos)", loc="left", fontsize=10.5, fontweight="bold")

    tempos = [float(np.mean([r["tempo"] for r in por_condicao[c]])) for c in CONDICOES]
    barras = ax_c.bar([NOMES_CONDICAO[c] for c in CONDICOES], tempos, 0.5, color=AZUL, linewidth=0)
    rotular_barras(ax_c, barras, lambda v: f"{v:.1f} s")
    ax_c.set_ylim(0, max(tempos) * 1.25)
    ax_c.yaxis.grid(True, color=GRADE, linewidth=0.8)
    ax_c.set_axisbelow(True)
    ax_c.set_title("Tempo médio por foto", loc="left", fontsize=10.5, fontweight="bold")
    salvar(fig, destino, "04_metricas_de_extracao.png")


def resumir(resultados):
    por_condicao = defaultdict(list)
    por_empresa = defaultdict(list)
    for r in resultados:
        por_condicao[r["condicao"]].append(r)
        por_empresa[r["empresa"]].append(r)

    def bloco(itens):
        return {
            "fotos": len(itens),
            "empresa_identificada": percentual([i["empresa_ok"] for i in itens]),
            "endereco_completo": percentual([i["tudo"] for i in itens]),
            "endereco_completo_sem_acentos": percentual([i["tudo_sem_acento"] for i in itens]),
            "confundiu_com_distrator": percentual([i["distrator"] for i in itens]),
            "marcadas_para_revisao": percentual([i["revisao"] for i in itens]),
            "tempo_medio_s": float(np.mean([i["tempo"] for i in itens])),
        }

    return {
        "geral": bloco(resultados),
        "por_condicao": {c: bloco(por_condicao[c]) for c in CONDICOES},
        "por_empresa": {e: bloco(por_empresa[e]) for e in por_empresa},
        "por_campo": {c: percentual([r["campos"][c] for r in resultados]) for c in CAMPOS},
    }


def main():
    parser = argparse.ArgumentParser(description="Gera as figuras do relatório técnico a partir do dataset sintético.")
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--sem-metricas", action="store_true", help="pula a avaliação completa e só gera as figuras do pipeline")
    args = parser.parse_args()
    args.saida.mkdir(parents=True, exist_ok=True)

    gabarito = carregar_gabarito()
    figura_deteccao(gabarito, args.saida)
    figura_preprocessamento(gabarito, args.saida)
    figura_extracao(gabarito, args.saida)

    if not args.sem_metricas:
        resultados = [avaliar(entrada, "auto") for entrada in gabarito.values()]
        figura_metricas(resultados, args.saida)
        resumo = resumir(resultados)
        caminho = args.saida / "resumo_metricas.json"
        caminho.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"gerado {caminho.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
