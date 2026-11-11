import argparse
import csv
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from citizentech_vision.document import rectify_document
from citizentech_vision.metrics import character_error_rate, word_error_rate
from citizentech_vision.ocr import read_text
from citizentech_vision.preprocess import VARIANTES, apply_variant, crop_relative

DADOS = RAIZ / "data"
SAIDA = DADOS / "output"
CONDICOES = ("frontal", "inclinada", "dificil")
PADRAO_CEP = re.compile(r"(\d{5})\D{0,2}(\d{3})")


def cep_correto(texto, esperado):
    encontrados = ["".join(m.groups()) for m in PADRAO_CEP.finditer(texto)]
    return esperado.replace("-", "") in encontrados


def carregar_rois():
    gabarito = json.loads((DADOS / "ground_truth" / "ground_truth.json").read_text(encoding="utf-8"))
    itens = []
    for entrada in gabarito:
        foto = cv2.imread(str(DADOS / entrada["foto"]))
        limpo = cv2.imread(str(DADOS / entrada["documento_limpo"]))
        retificado = rectify_document(foto, tamanho=(limpo.shape[1], limpo.shape[0])).imagem
        regiao = entrada["regiao_endereco"]
        itens.append(
            {
                "id": entrada["id"],
                "empresa": entrada["empresa"],
                "condicao": entrada["condicao"],
                "cep": entrada["endereco"]["cep"],
                "referencia": "\n".join(entrada["linhas_impressas"]),
                "roi": crop_relative(retificado, regiao),
                "roi_limpo": crop_relative(limpo, regiao),
            }
        )
    return itens


def avaliar(itens, preparar, chave_roi, idioma, psm):
    resultados = []
    for item in itens:
        inicio = time.perf_counter()
        texto = read_text(preparar(item[chave_roi]), idioma=idioma, psm=psm)
        tempo = time.perf_counter() - inicio
        resultados.append(
            {
                "id": item["id"],
                "empresa": item["empresa"],
                "condicao": item["condicao"],
                "cer": character_error_rate(item["referencia"], texto),
                "cer_sem_acentos": character_error_rate(item["referencia"], texto, sem_acentos=True),
                "wer": word_error_rate(item["referencia"], texto),
                "cep_ok": cep_correto(texto, item["cep"]),
                "tempo": tempo,
                "texto": texto,
            }
        )
    return resultados


def resumir(resultados):
    por_condicao = defaultdict(list)
    for r in resultados:
        por_condicao[r["condicao"]].append(r["cer"])
    linha = {c: float(np.mean(por_condicao[c])) for c in CONDICOES}
    linha["cer"] = float(np.mean([r["cer"] for r in resultados]))
    linha["cer_sem_acentos"] = float(np.mean([r["cer_sem_acentos"] for r in resultados]))
    linha["wer"] = float(np.mean([r["wer"] for r in resultados]))
    linha["cep"] = float(np.mean([r["cep_ok"] for r in resultados]))
    linha["tempo"] = float(np.mean([r["tempo"] for r in resultados]))
    return linha


def imprimir_tabela(titulo, linhas):
    print(f"\n{titulo}")
    cabecalho = (
        f"{'variante':44s} {'frontal':>8s} {'inclin.':>8s} {'dificil':>8s} "
        f"{'CER':>7s} {'CER s/ac':>9s} {'WER':>7s} {'CEP ok':>7s} {'s/ROI':>6s}"
    )
    print(cabecalho)
    for nome, r in linhas.items():
        print(
            f"{nome:44s} {r['frontal']:8.3f} {r['inclinada']:8.3f} {r['dificil']:8.3f} "
            f"{r['cer']:7.3f} {r['cer_sem_acentos']:9.3f} {r['wer']:7.3f} "
            f"{r['cep']:7.0%} {r['tempo']:6.2f}"
        )


def salvar_csv(caminho, resultados_por_nome):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["variante", "id", "empresa", "condicao", "cer", "cer_sem_acentos", "wer", "cep_ok", "tempo"])
        for nome, resultados in resultados_por_nome.items():
            for r in resultados:
                escritor.writerow(
                    [nome, r["id"], r["empresa"], r["condicao"], f"{r['cer']:.4f}",
                     f"{r['cer_sem_acentos']:.4f}", f"{r['wer']:.4f}", int(r["cep_ok"]), f"{r['tempo']:.3f}"]
                )


def main():
    parser = argparse.ArgumentParser(description="Compara variantes de pré-processamento no OCR do endereço.")
    parser.add_argument("--lang", default="por")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--variante", nargs="+", choices=list(VARIANTES), help="avalia apenas estas variantes")
    parser.add_argument("--varrer-psm", metavar="VARIANTE", help="compara valores de --psm para esta variante")
    args = parser.parse_args()

    itens = carregar_rois()
    print(f"{len(itens)} recortes de endereço (fotos retificadas)")

    if args.varrer_psm:
        linhas = {}
        for psm in (3, 4, 6, 7, 11, 13):
            resultados = avaliar(itens, lambda im: apply_variant(im, args.varrer_psm), "roi", args.lang, psm)
            linhas[f"{args.varrer_psm} | psm {psm}"] = resumir(resultados)
        imprimir_tabela("Variação do --psm", linhas)
        return

    nomes = args.variante or list(VARIANTES)
    linhas = {}
    resultados_por_nome = {}
    referencia = avaliar(itens, lambda im: im, "roi_limpo", args.lang, args.psm)
    linhas["referência: documento limpo, sem pré-proc."] = resumir(referencia)
    for nome in nomes:
        resultados = avaliar(itens, lambda im, n=nome: apply_variant(im, n), "roi", args.lang, args.psm)
        linhas[nome] = resumir(resultados)
        resultados_por_nome[nome] = resultados
    imprimir_tabela(f"Pré-processamento (psm {args.psm}, lang {args.lang})", linhas)
    if not args.variante:
        salvar_csv(SAIDA / "preprocessing_experiments.csv", resultados_por_nome)


if __name__ == "__main__":
    main()
