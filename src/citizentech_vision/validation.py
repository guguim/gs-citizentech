import re
from typing import NamedTuple

from .address import CAMPOS, UFS

OBRIGATORIOS = ("logradouro", "numero", "cidade", "uf", "cep")
PADRAO_CEP_FINAL = re.compile(r"^\d{5}-\d{3}$")
PADRAO_NUMERO = re.compile(r"^(\d{1,5}[A-Z]?|S/N|SN)$")

FAIXAS_CEP_POR_UF = {
    "SP": ((1000, 19999),),
    "RJ": ((20000, 28999),),
    "ES": ((29000, 29999),),
    "MG": ((30000, 39999),),
    "BA": ((40000, 48999),),
    "SE": ((49000, 49999),),
    "PE": ((50000, 56999),),
    "AL": ((57000, 57999),),
    "PB": ((58000, 58999),),
    "RN": ((59000, 59999),),
    "CE": ((60000, 63999),),
    "PI": ((64000, 64999),),
    "MA": ((65000, 65999),),
    "PA": ((66000, 68899),),
    "AP": ((68900, 68999),),
    "AM": ((69000, 69299), (69400, 69899)),
    "RR": ((69300, 69399),),
    "AC": ((69900, 69999),),
    "DF": ((70000, 72799), (73000, 73699)),
    "GO": ((72800, 72999), (73700, 76799)),
    "RO": ((76800, 76999),),
    "TO": ((77000, 77995),),
    "MT": ((78000, 78899),),
    "MS": ((79000, 79999),),
    "PR": ((80000, 87999),),
    "SC": ((88000, 89999),),
    "RS": ((90000, 99999),),
}


PALAVRAS_LIGACAO = {"de", "da", "do", "das", "dos", "e", "em", "a", "o"}
PADRAO_ROMANO = re.compile(r"^[IVXLC]{1,4}$")


def suspicious_words(texto):
    suspeitas = []
    for palavra in texto.split():
        limpa = palavra.strip(".,-")
        if not limpa or any(c.isdigit() for c in limpa):
            continue
        baixa = limpa.lower()
        if baixa in PALAVRAS_LIGACAO or PADRAO_ROMANO.match(limpa):
            continue
        if len(limpa) == 1 and limpa.isupper():
            continue
        if len(limpa) <= 2 or limpa[0].islower():
            suspeitas.append(palavra)
    return suspeitas


class Problema(NamedTuple):
    campo: str
    mensagem: str


def uf_from_zip(cep):
    prefixo = int(cep[:5])
    for uf, faixas in FAIXAS_CEP_POR_UF.items():
        if any(inicio <= prefixo <= fim for inicio, fim in faixas):
            return uf
    return None


def infer_state(campos):
    cep = campos.get("cep", "")
    if campos.get("uf") or not PADRAO_CEP_FINAL.match(cep):
        return ""
    return uf_from_zip(cep) or ""


def validate_address(campos):
    problemas = []
    for campo in OBRIGATORIOS:
        if not campos.get(campo):
            problemas.append(Problema(campo, "campo obrigatório não encontrado"))

    cep = campos.get("cep", "")
    if cep and not PADRAO_CEP_FINAL.match(cep):
        problemas.append(Problema("cep", "formato de CEP inválido"))
    elif cep and cep.replace("-", "") == "00000000":
        problemas.append(Problema("cep", "CEP inválido"))

    uf = campos.get("uf", "")
    if uf and uf not in UFS:
        problemas.append(Problema("uf", "UF inexistente"))

    if cep and PADRAO_CEP_FINAL.match(cep) and uf in UFS:
        esperada = uf_from_zip(cep)
        if esperada is not None and esperada != uf:
            problemas.append(Problema("cep", f"CEP não pertence à faixa de {uf}"))

    numero = campos.get("numero", "")
    if numero and not PADRAO_NUMERO.match(numero):
        problemas.append(Problema("numero", "número com formato suspeito"))

    cidade = campos.get("cidade", "")
    if cidade and (len(cidade) < 3 or any(c.isdigit() for c in cidade)):
        problemas.append(Problema("cidade", "nome de cidade suspeito"))

    if not campos.get("bairro"):
        problemas.append(Problema("bairro", "bairro não encontrado"))

    for campo in ("logradouro", "bairro"):
        suspeitas = suspicious_words(campos.get(campo, ""))
        if suspeitas:
            problemas.append(Problema(campo, f"termo suspeito: {', '.join(suspeitas)}"))

    return problemas


def fields_to_review(problemas):
    return [c for c in CAMPOS if any(p.campo == c for p in problemas)]
