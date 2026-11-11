import re
from dataclasses import dataclass, field

from .cities import match_city

UFS = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)

CAMPOS = ("logradouro", "numero", "complemento", "bairro", "cidade", "uf", "cep")

TIPOS_LOGRADOURO = {
    "R": "Rua",
    "AV": "Avenida",
    "AL": "Alameda",
    "TV": "Travessa",
    "TRAV": "Travessa",
    "PC": "Praça",
    "ROD": "Rodovia",
    "EST": "Estrada",
}

TERMOS_COMPLEMENTO = {
    "AP": "Apto",
    "APTO": "Apto",
    "APARTAMENTO": "Apto",
    "BL": "Bloco",
    "BLOCO": "Bloco",
    "CS": "Casa",
    "CASA": "Casa",
    "FDS": "Fundos",
    "FUNDOS": "Fundos",
    "SL": "Sala",
    "SALA": "Sala",
    "CJ": "Conjunto",
    "CONJ": "Conjunto",
    "LJ": "Loja",
    "LOJA": "Loja",
}

PALAVRAS_MINUSCULAS = {"de", "da", "do", "das", "dos", "e"}

SEPARADORES_CONFUSOS = re.compile(r"[«»·•–—|~]")
PADRAO_CEP = re.compile(r"(?<!\d)(\d{5})\s*[-.:]?\s*(\d{3})(?!\d)")
ROTULO_CEP = re.compile(r"\bCEP\b[:.\s]*", re.IGNORECASE)
PADRAO_RUA = re.compile(
    r"^(?P<log>.+?)\s*[,.]\s*(?P<num>\d+[A-Za-z]?|S/N|SN)\b(?P<resto>.*)$", re.IGNORECASE
)
PADRAO_RUA_SEM_VIRGULA = re.compile(
    r"^(?P<log>.+?)\s+(?P<num>\d+[A-Za-z]?)\b(?P<resto>.*)$", re.IGNORECASE
)
PADRAO_UF_FINAL = re.compile(r"(?:^|[\s/\-])([A-Za-z]{2})[\s\-.,]*$")
PADRAO_COMPLEMENTO = re.compile(
    r"^(?:(?:BLOCO|BL)\s+\w+\s+)?(?:(?:APTO|AP|APARTAMENTO|CASA|CS|SALA|SL|CJ|CONJ|LOJA|LJ)\s*\d+\w?)$"
    r"|^(?:BLOCO|BL)\s+\w+$|^(?:FUNDOS|FDS)$",
    re.IGNORECASE,
)


@dataclass
class ParsedAddress:
    logradouro: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    cidade: str = ""
    uf: str = ""
    cep: str = ""
    origem: dict = field(default_factory=dict)
    avisos: list = field(default_factory=list)
    conf_campo: dict = field(default_factory=dict)
    sem_virgula: bool = False

    def as_dict(self):
        return {campo: getattr(self, campo) for campo in CAMPOS}


def normalize_line(linha):
    linha = linha.replace("€", "C").replace("¢", "C")
    linha = SEPARADORES_CONFUSOS.sub(" - ", linha)
    return " ".join(linha.split())


def strip_edges(texto):
    return re.sub(r"^[\s\-/.,:]+|[\s\-/.,:]+$", "", texto)


def has_content(linha):
    return sum(c.isalnum() for c in linha) >= 3


def smart_title(texto):
    letras = [c for c in texto if c.isalpha()]
    if not letras or sum(c.isupper() for c in letras) / len(letras) < 0.7:
        return texto
    palavras = []
    for i, palavra in enumerate(texto.split()):
        baixa = palavra.lower()
        if len(palavra) == 1 and palavra.isalpha():
            palavras.append(palavra.upper())
        elif re.fullmatch(r"[IVXLC]{2,4}", palavra):
            palavras.append(palavra)
        elif i > 0 and baixa in PALAVRAS_MINUSCULAS:
            palavras.append(baixa)
        else:
            palavras.append(baixa.capitalize())
    return " ".join(palavras)


def fix_roman_suffix(logradouro):
    palavras = logradouro.split()
    if len(palavras) >= 3 and palavras[-1].lower() in {"il", "ii", "li", "ll", "l1", "i1"}:
        palavras[-1] = "II"
    return " ".join(palavras)


def looks_like_complement(texto):
    letras = sum(c.isalpha() for c in texto)
    return len(texto) <= 12 and any(c.isdigit() for c in texto) and letras <= 6


def expand_street_type(logradouro):
    partes = logradouro.split(" ", 1)
    chave = partes[0].rstrip(".").upper()
    if chave in TIPOS_LOGRADOURO and len(partes) > 1:
        return f"{TIPOS_LOGRADOURO[chave]} {partes[1]}"
    return logradouro


def expand_complement(complemento):
    palavras = []
    for palavra in complemento.split():
        palavras.append(TERMOS_COMPLEMENTO.get(palavra.upper().rstrip("."), palavra))
    return " ".join(palavras)


def is_complement(texto):
    return bool(PADRAO_COMPLEMENTO.match(texto.strip()))


def find_street(linhas):
    for indice, linha in enumerate(linhas):
        encontrado = PADRAO_RUA.match(linha)
        if encontrado:
            return indice, encontrado, False
    for indice, linha in enumerate(linhas):
        encontrado = PADRAO_RUA_SEM_VIRGULA.match(linha)
        if encontrado:
            return indice, encontrado, True
    return None, None, False


def take_zip(trabalho):
    for posicao, (origem, texto) in enumerate(trabalho):
        encontrado = PADRAO_CEP.search(texto)
        if encontrado:
            cep = f"{encontrado.group(1)}-{encontrado.group(2)}"
            limpo = PADRAO_CEP.sub(" ", texto, count=1)
            limpo = strip_edges(ROTULO_CEP.sub(" ", limpo))
            trabalho[posicao] = (origem, limpo)
            return cep, origem
    return "", None


def take_state_line(trabalho):
    for posicao in range(len(trabalho) - 1, -1, -1):
        origem, texto = trabalho[posicao]
        encontrado = PADRAO_UF_FINAL.search(texto)
        if encontrado and encontrado.group(1).upper() in UFS:
            restante = strip_edges(texto[: encontrado.start(1)])
            return posicao, encontrado.group(1).upper(), restante
    return None, "", ""


def attach_confidence(parsed, linhas):
    for campo, indice in parsed.origem.items():
        if indice < len(linhas) and linhas[indice].palavras:
            linha = linhas[indice]
            parsed.conf_campo[campo] = (linha.confianca, min(p.confianca for p in linha.palavras))
    return parsed


def split_parts(texto):
    return [strip_edges(p) for p in re.split(r"\s+-\s+", texto) if strip_edges(p)]


def find_city_line_without_state(trabalho):
    for posicao in range(len(trabalho) - 1, 0, -1):
        _, texto = trabalho[posicao]
        if not has_content(texto) or is_complement(texto):
            continue
        partes = split_parts(texto)
        if partes and match_city(partes[-1]):
            return posicao, texto
    return None, ""


def set_complement(resultado, texto, origem):
    resultado.complemento = smart_title(expand_complement(texto))
    resultado.origem["complemento"] = origem
    if not is_complement(texto):
        resultado.avisos.append(("complemento", "formato do complemento não reconhecido"))


def parse_address_lines(linhas):
    normalizadas = [(i, normalize_line(l)) for i, l in enumerate(linhas)]
    normalizadas = [(i, l) for i, l in normalizadas if has_content(l)]
    resultado = ParsedAddress()

    indice, rua, sem_virgula = find_street([l for _, l in normalizadas])
    if rua is None:
        return resultado
    origem_rua = normalizadas[indice][0]
    resultado.sem_virgula = sem_virgula
    logradouro = expand_street_type(smart_title(strip_edges(rua.group("log"))))
    resultado.logradouro = fix_roman_suffix(logradouro)
    resultado.numero = rua.group("num").upper()
    resultado.origem["logradouro"] = origem_rua
    resultado.origem["numero"] = origem_rua

    trabalho = [(origem_rua, rua.group("resto"))] + normalizadas[indice + 1:]

    cep, origem_cep = take_zip(trabalho)
    if cep:
        resultado.cep = cep
        resultado.origem["cep"] = origem_cep

    candidatos_bairro = []
    posicao_cidade, uf, restante = take_state_line(trabalho)
    if posicao_cidade is None:
        posicao_cidade, restante = find_city_line_without_state(trabalho)
        if posicao_cidade is not None:
            resultado.avisos.append(("uf", "UF não encontrada no texto"))
    else:
        resultado.uf = uf
        resultado.origem["uf"] = trabalho[posicao_cidade][0]

    if posicao_cidade is not None:
        origem_cidade = trabalho[posicao_cidade][0]
        partes = split_parts(restante)
        if partes:
            resultado.cidade = match_city(partes[-1]) or smart_title(partes[-1])
            resultado.origem["cidade"] = origem_cidade
            if len(partes) > 1:
                candidatos_bairro.append((" - ".join(partes[:-1]), origem_cidade, 1))

    for posicao, (origem, texto) in enumerate(trabalho):
        if posicao == 0:
            itens = split_parts(texto)
            if len(itens) >= 2:
                set_complement(resultado, " ".join(itens[:-1]), origem)
                candidatos_bairro.append((itens[-1], origem, 2))
            elif itens:
                item = itens[0]
                complemento = is_complement(item) or (
                    looks_like_complement(item) and posicao_cidade is not None
                )
                if complemento:
                    set_complement(resultado, item, origem)
                else:
                    candidatos_bairro.append((item, origem, 2))
            continue
        if posicao == posicao_cidade or not has_content(texto):
            continue
        texto = strip_edges(texto)
        if is_complement(texto) and not resultado.complemento:
            set_complement(resultado, texto, origem)
        else:
            candidatos_bairro.append((texto, origem, 0))

    if candidatos_bairro:
        texto, origem, _ = min(candidatos_bairro, key=lambda c: c[2])
        resultado.bairro = smart_title(texto)
        resultado.origem["bairro"] = origem

    return resultado
