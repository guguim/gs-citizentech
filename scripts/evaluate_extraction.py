import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from citizentech_vision.address import CAMPOS
from citizentech_vision.extraction import METODOS, extract_address
from citizentech_vision.metrics import normalize_text

DADOS = RAIZ / "data"
CONDICOES = ("frontal", "inclinada", "dificil")


def same(esperado, obtido, sem_acentos=False):
    return normalize_text(esperado, sem_acentos) == normalize_text(obtido, sem_acentos)


def cep_digits(texto):
    return "".join(c for c in texto if c.isdigit())


def avaliar(entrada, metodo):
    foto = cv2.imread(str(DADOS / entrada["foto"]))
    inicio = time.perf_counter()
    resultado = extract_address(foto, metodo=metodo)
    tempo = time.perf_counter() - inicio

    esperado = entrada["endereco"]
    campos = {c: same(esperado[c], resultado.campos.get(c, "")) for c in CAMPOS}
    campos_sem_acento = {c: same(esperado[c], resultado.campos.get(c, ""), True) for c in CAMPOS}
    ceps_distratores = {cep_digits(d.split("CEP")[-1]) for d in entrada["enderecos_distratores"]}
    obtido_cep = cep_digits(resultado.campos.get("cep", ""))
    return {
        "id": entrada["id"],
        "empresa": entrada["empresa"],
        "condicao": entrada["condicao"],
        "empresa_ok": resultado.empresa == entrada["empresa"],
        "campos": campos,
        "tudo": all(campos.values()),
        "tudo_sem_acento": all(campos_sem_acento.values()),
        "distrator": bool(obtido_cep) and obtido_cep in ceps_distratores,
        "revisao": resultado.precisa_revisao,
        "revisar": resultado.campos_revisar,
        "confianca": resultado.confianca,
        "metodo": resultado.metodo,
        "tempo": tempo,
        "esperado": esperado,
        "obtido": resultado.campos,
        "problemas": resultado.problemas,
    }


def pct(valores):
    return f"{np.mean(valores):6.0%}"


def tabela(titulo, grupos):
    print(f"\n{titulo}")
    cabecalho = f"{'grupo':12s} {'n':>3s} {'empresa':>8s} {'endereço':>9s} {'s/acento':>9s} {'distrator':>10s} {'revisão':>8s} {'s/foto':>7s}"
    print(cabecalho)
    for nome, itens in grupos.items():
        print(
            f"{nome:12s} {len(itens):3d} {pct([i['empresa_ok'] for i in itens]):>8s} "
            f"{pct([i['tudo'] for i in itens]):>9s} {pct([i['tudo_sem_acento'] for i in itens]):>9s} "
            f"{pct([i['distrator'] for i in itens]):>10s} {pct([i['revisao'] for i in itens]):>8s} "
            f"{np.mean([i['tempo'] for i in itens]):7.2f}"
        )


def tabela_campos(resultados):
    print("\nAcerto por campo (todas as fotos)")
    for campo in CAMPOS:
        print(f"  {campo:12s} {pct([r['campos'][campo] for r in resultados])}")


def listar_erros(resultados):
    erros = [r for r in resultados if not r["tudo"]]
    print(f"\nFotos com algum campo diferente do gabarito: {len(erros)}")
    for r in erros:
        diferentes = {c: (r["esperado"][c], r["obtido"].get(c, "")) for c in CAMPOS if not r["campos"][c]}
        print(f"- {r['id']} (metodo {r['metodo']}, revisão {'sim' if r['revisao'] else 'não'}, campos a revisar {r['revisar']})")
        for campo, (esp, obt) in diferentes.items():
            print(f"    {campo}: esperado {esp!r} | obtido {obt!r}")


def main():
    parser = argparse.ArgumentParser(description="Avalia a extração de endereço nas fotos sintéticas.")
    parser.add_argument("--metodo", choices=METODOS, default="auto")
    parser.add_argument("--condicao", choices=CONDICOES)
    parser.add_argument("--saida", type=Path, help="grava o detalhe por foto em JSON")
    args = parser.parse_args()

    gabarito = json.loads((DADOS / "ground_truth" / "ground_truth.json").read_text(encoding="utf-8"))
    if args.condicao:
        gabarito = [e for e in gabarito if e["condicao"] == args.condicao]

    resultados = [avaliar(e, args.metodo) for e in gabarito]

    por_condicao = defaultdict(list)
    por_empresa = defaultdict(list)
    for r in resultados:
        por_condicao[r["condicao"]].append(r)
        por_empresa[r["empresa"]].append(r)

    print(f"Método: {args.metodo} | {len(resultados)} fotos")
    tabela("Por condição", {c: por_condicao[c] for c in CONDICOES if por_condicao[c]})
    tabela("Por empresa", dict(por_empresa))
    tabela("Geral", {"todas": resultados})
    tabela_campos(resultados)
    listar_erros(resultados)

    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
