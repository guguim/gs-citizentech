from collections import Counter

from .address import CAMPOS, ParsedAddress
from .metrics import normalize_text


def merge_candidates(candidatos):
    resultado = ParsedAddress()
    divergentes = []
    for campo in CAMPOS:
        valores = [(normalize_text(getattr(c, campo)), c) for c in candidatos if getattr(c, campo)]
        if not valores:
            continue
        contagem = Counter(v for v, _ in valores)
        melhor = max(contagem.values())
        escolhido = next(c for v, c in valores if contagem[v] == melhor)
        setattr(resultado, campo, getattr(escolhido, campo))
        if campo in escolhido.conf_campo:
            resultado.conf_campo[campo] = escolhido.conf_campo[campo]
        if len(contagem) > 1 or len(valores) < len(candidatos):
            divergentes.append(campo)
    resultado.avisos = list(candidatos[0].avisos)
    resultado.sem_virgula = candidatos[0].sem_virgula
    return resultado, divergentes
