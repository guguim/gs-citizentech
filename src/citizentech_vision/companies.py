from dataclasses import dataclass

from .document import DOCUMENT_SIZE

LARGURA, ALTURA = DOCUMENT_SIZE
REGIAO_CABECALHO = (0.0, 0.0, 1.0, 0.14)


def relative_zone(caixa):
    x0, y0, x1, y1 = caixa
    return (x0 / LARGURA, y0 / ALTURA, x1 / LARGURA, y1 / ALTURA)


@dataclass(frozen=True)
class CompanyConfig:
    nome: str
    palavras_chave: tuple
    zona_endereco: tuple


EMPRESAS = {
    "enel": CompanyConfig(
        nome="enel",
        palavras_chave=(("ENEL", 1.0), ("DISTRIBUICAO", 0.4), ("ENERGIA", 0.4)),
        zona_endereco=relative_zone((50, 296, 880, 520)),
    ),
    "sabesp": CompanyConfig(
        nome="sabesp",
        palavras_chave=(("SABESP", 1.0), ("SANEAMENTO", 0.4), ("ESGOTO", 0.4)),
        zona_endereco=relative_zone((50, 286, 1190, 425)),
    ),
    "claro": CompanyConfig(
        nome="claro",
        palavras_chave=(("CLARO", 1.0), ("FATURADESERVICOS", 0.4)),
        zona_endereco=relative_zone((50, 240, 690, 420)),
    ),
}

ROTULOS_ENDERECO_CLIENTE = (
    "ENDERECODAUNIDADECONSUMIDORA",
    "ENDERECODOIMOVEL",
    "ENDERECODECOBRANCA",
    "ENDERECODEENTREGA",
    "ENDERECODOCLIENTE",
    "ENDERECODEINSTALACAO",
    "ENDERECODECORRESPONDENCIA",
)

ROTULOS_OUTROS_ENDERECOS = (
    "AGENCIA",
    "ATENDIMENTO",
    "LOJAS",
    "SEDE",
    "CNPJ",
    "PAGAMENTO",
    "ADMINISTRATIVA",
    "FILIAL",
    "MATRIZ",
)
