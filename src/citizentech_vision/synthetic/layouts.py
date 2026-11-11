from dataclasses import dataclass

from PIL import Image, ImageDraw

from .fake_data import generate_address
from .fonts import load_font

PAGE_SIZE = (1240, 1754)

ABREVIACOES_LOGRADOURO = {"Rua": "R", "Avenida": "AV", "Alameda": "AL", "Travessa": "TV"}
ABREVIACOES_COMPLEMENTO = {"Apto": "AP", "Bloco": "BL", "Casa": "CS", "Fundos": "FDS", "Sala": "SL"}

CINZA = (110, 110, 110)
BRANCO = (255, 255, 255)

ROI_ENEL = (50, 325, 860, 520)
ROI_SABESP = (50, 312, 1190, 420)
ROI_CLARO = (50, 268, 670, 420)


@dataclass
class RenderedDocument:
    image: Image.Image
    linhas_endereco: list
    regiao_endereco: tuple
    caixa_texto_endereco: tuple
    enderecos_distratores: list


class Page:
    def __init__(self):
        self.image = Image.new("RGB", PAGE_SIZE, BRANCO)
        self.draw = ImageDraw.Draw(self.image)

    def text(self, xy, conteudo, tamanho=24, negrito=False, cor=(25, 25, 25)):
        fonte = load_font(tamanho, negrito)
        self.draw.text(xy, conteudo, font=fonte, fill=cor)
        return self.draw.textbbox(xy, conteudo, font=fonte)

    def block(self, xy, linhas, tamanho=26, negrito=False, cor=(25, 25, 25), espaco=14):
        x, y = xy
        caixas = []
        for linha in linhas:
            caixa = self.text((x, y), linha, tamanho, negrito, cor)
            caixas.append(caixa)
            y = caixa[3] + espaco
        return union(caixas)

    def rectangle(self, caixa, fill=None, outline=None, width=2):
        self.draw.rectangle(caixa, fill=fill, outline=outline, width=width)

    def line(self, pontos, fill=(210, 210, 210), width=2):
        self.draw.line(pontos, fill=fill, width=width)


def union(caixas):
    return (
        min(c[0] for c in caixas),
        min(c[1] for c in caixas),
        max(c[2] for c in caixas),
        max(c[3] for c in caixas),
    )


def relative_box(caixa):
    largura, altura = PAGE_SIZE
    return (
        round(caixa[0] / largura, 4),
        round(caixa[1] / altura, 4),
        round(caixa[2] / largura, 4),
        round(caixa[3] / altura, 4),
    )


def random_digits(rng, quantidade):
    return "".join(rng.choice("0123456789") for _ in range(quantidade))


def random_date(rng):
    return f"{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}/2026"


def money(rng, minimo, maximo):
    return f"{rng.uniform(minimo, maximo):.2f}".replace(".", ",")


def single_line_address(endereco):
    return (
        f"{endereco.logradouro}, {endereco.numero} - {endereco.bairro} - "
        f"{endereco.cidade}/{endereco.uf} - CEP {endereco.cep}"
    )


def two_line_address(endereco):
    return [
        f"{endereco.logradouro}, {endereco.numero} - {endereco.bairro}",
        f"{endereco.cidade}/{endereco.uf} - CEP {endereco.cep}",
    ]


def abbreviate_complement(complemento):
    palavras = [ABREVIACOES_COMPLEMENTO.get(p, p) for p in complemento.split()]
    return " ".join(palavras)


def label_value(page, xy, rotulo, valor):
    x, y = xy
    page.text((x, y), rotulo, 15, True, CINZA)
    page.text((x, y + 22), valor, 24, True)


def draw_table(page, topo, colunas, linhas, cor_cabecalho, limites=(60, 1180)):
    esquerda, direita = limites
    page.rectangle((esquerda, topo, direita, topo + 48), fill=cor_cabecalho)
    for titulo, x in colunas:
        page.text((x, topo + 11), titulo, 22, True, BRANCO)
    y = topo + 48
    for linha in linhas:
        for (_, x), valor in zip(colunas, linha):
            page.text((x, y + 11), valor, 22)
        y += 46
        page.line((esquerda, y, direita, y))
    return y


def draw_barcode(page, rng, topo, esquerda=60, direita=1180, altura=90):
    x = esquerda
    while x < direita:
        largura = rng.choice([2, 3, 4, 6])
        if rng.random() < 0.6:
            page.rectangle((x, topo, x + largura, topo + altura), fill=(0, 0, 0), width=0)
        x += largura + rng.choice([2, 3, 5])
    page.text((esquerda, topo + altura + 10), random_digits(rng, 44), 20)


def draw_synthetic_mark(page):
    page.text((60, 1705), "DOCUMENTO SINTÉTICO PARA TESTES - SEM VALOR LEGAL", 18, False, (140, 140, 140))


def enel_lines(endereco):
    primeira = f"{endereco.logradouro}, {endereco.numero}"
    if endereco.complemento:
        primeira += f" - {endereco.complemento}"
    return [
        primeira.upper(),
        endereco.bairro.upper(),
        f"CEP {endereco.cep} - {endereco.cidade} - {endereco.uf}".upper(),
    ]


def sabesp_lines(endereco):
    tipo, nome = endereco.logradouro.split(" ", 1)
    primeira = f"{ABREVIACOES_LOGRADOURO[tipo]} {nome}, {endereco.numero}"
    if endereco.complemento:
        primeira += f" {abbreviate_complement(endereco.complemento)}"
    primeira += f" - {endereco.bairro}"
    return [
        primeira.upper(),
        f"{endereco.cidade} - {endereco.uf} - {endereco.cep}".upper(),
    ]


def claro_lines(endereco):
    primeira = f"{endereco.logradouro}, {endereco.numero}"
    if endereco.complemento:
        primeira += f" - {endereco.complemento}"
    return [
        primeira,
        f"{endereco.bairro} - {endereco.cidade}/{endereco.uf}",
        f"CEP {endereco.cep}",
    ]


def render_enel(cliente, rng):
    page = Page()
    page.rectangle((0, 0, PAGE_SIZE[0], 170), fill=(70, 30, 110))
    page.text((60, 45), "Enel Distribuição São Paulo", 46, True, BRANCO)
    page.text((60, 112), "CONTA DE ENERGIA ELÉTRICA", 26, False, (230, 220, 245))

    page.text((60, 215), "DADOS DO CLIENTE", 20, True, CINZA)
    page.text((60, 250), cliente.nome.upper(), 30, True)
    page.text((60, 300), "ENDEREÇO DA UNIDADE CONSUMIDORA", 18, True, CINZA)
    linhas = enel_lines(cliente.endereco)
    caixa = page.block((60, 335), linhas, 25)

    page.rectangle((900, 215, 1190, 500), outline=(180, 180, 180))
    label_value(page, (920, 228), "Nº DO CLIENTE", random_digits(rng, 9))
    label_value(page, (920, 298), "INSTALAÇÃO", random_digits(rng, 10))
    label_value(page, (920, 368), "VENCIMENTO", random_date(rng))
    label_value(page, (920, 438), "TOTAL A PAGAR (R$)", money(rng, 80, 640))

    kwh = rng.randint(120, 520)
    colunas = [("Descrição", 70), ("Quantidade", 620), ("Tarifa", 810), ("Valor (R$)", 1010)]
    linhas_tabela = [
        ["Consumo de energia elétrica", f"{kwh} kWh", "0,92", money(rng, 90, 480)],
        ["Contribuição de iluminação pública", "", "", money(rng, 8, 40)],
        ["Bandeira tarifária", "", "", money(rng, 0, 30)],
        ["ICMS", "", "18%", money(rng, 10, 90)],
        ["PIS/COFINS", "", "", money(rng, 3, 25)],
    ]
    draw_table(page, 620, colunas, linhas_tabela, (70, 30, 110))

    agencia = generate_address(rng)
    page.text((60, 1020), "LOCAL DE PAGAMENTO", 18, True, CINZA)
    page.text((60, 1050), "Rede bancária e casas lotéricas. Agência de atendimento ao cliente:", 22)
    page.block((60, 1090), two_line_address(agencia), 22, espaco=10)

    draw_barcode(page, rng, 1300)

    sede = generate_address(rng)
    page.text((60, 1520), "Enel Distribuição São Paulo S.A. - CNPJ 00.000.000/0001-00", 20, True)
    page.block((60, 1555), two_line_address(sede), 20, espaco=8)
    page.text((60, 1635), "SAC 0800 000 0000", 20)
    draw_synthetic_mark(page)

    return RenderedDocument(
        image=page.image,
        linhas_endereco=linhas,
        regiao_endereco=relative_box(ROI_ENEL),
        caixa_texto_endereco=caixa,
        enderecos_distratores=[single_line_address(agencia), single_line_address(sede)],
    )


def render_sabesp(cliente, rng):
    page = Page()
    page.rectangle((0, 0, PAGE_SIZE[0], 24), fill=(0, 82, 155))
    page.text((60, 55), "Sabesp", 58, True, (0, 82, 155))
    page.text((60, 130), "Companhia de Saneamento Básico - CONTA DE ÁGUA E ESGOTO", 22, False, CINZA)
    page.text((860, 70), "Nº DA CONTA", 15, True, CINZA)
    page.text((860, 92), random_digits(rng, 12), 26, True)

    page.line((60, 190, 1180, 190), fill=(0, 82, 155), width=3)
    page.text((60, 215), "CLIENTE", 18, True, CINZA)
    page.text((60, 242), cliente.nome.upper(), 30, True)
    page.text((60, 290), "ENDEREÇO DO IMÓVEL", 16, True, CINZA)
    linhas = sabesp_lines(cliente.endereco)
    caixa = page.block((60, 318), linhas, 25)

    page.rectangle((60, 470, 600, 700), outline=(180, 180, 180))
    page.text((80, 482), "DADOS DA LIGAÇÃO", 18, True, (0, 82, 155))
    label_value(page, (80, 520), "RGI", random_digits(rng, 10))
    label_value(page, (80, 590), "HIDRÔMETRO", "A" + random_digits(rng, 9))
    label_value(page, (330, 520), "LEITURA ANTERIOR", random_digits(rng, 4))
    label_value(page, (330, 590), "LEITURA ATUAL", random_digits(rng, 4))

    page.rectangle((640, 470, 1180, 700), outline=(180, 180, 180))
    page.text((660, 482), "RESUMO DA CONTA", 18, True, (0, 82, 155))
    label_value(page, (660, 520), "VENCIMENTO", random_date(rng))
    label_value(page, (660, 590), "TOTAL A PAGAR (R$)", money(rng, 40, 380))

    colunas = [("Serviço", 70), ("Consumo", 640), ("Valor (R$)", 1000)]
    linhas_tabela = [
        ["Água", f"{rng.randint(5, 30)} m³", money(rng, 30, 180)],
        ["Esgoto", f"{rng.randint(5, 30)} m³", money(rng, 30, 180)],
        ["Tarifa social", "", money(rng, 0, 20)],
        ["Outros serviços", "", money(rng, 0, 15)],
    ]
    draw_table(page, 760, colunas, linhas_tabela, (0, 82, 155))

    loja = generate_address(rng)
    page.text((60, 1130), "UNIDADE DE ATENDIMENTO PRESENCIAL", 18, True, CINZA)
    page.block((60, 1165), two_line_address(loja), 22, espaco=10)

    draw_barcode(page, rng, 1330)

    sede = generate_address(rng)
    page.text((60, 1560), "Sede administrativa", 18, True, CINZA)
    page.block((60, 1590), two_line_address(sede), 20, espaco=8)
    draw_synthetic_mark(page)

    return RenderedDocument(
        image=page.image,
        linhas_endereco=linhas,
        regiao_endereco=relative_box(ROI_SABESP),
        caixa_texto_endereco=caixa,
        enderecos_distratores=[single_line_address(loja), single_line_address(sede)],
    )


def render_claro(cliente, rng):
    page = Page()
    page.text((60, 55), "Claro", 64, True, (215, 25, 32))
    page.text((60, 140), "FATURA DE SERVIÇOS", 24, True, CINZA)
    page.line((60, 190, 1180, 190), fill=(215, 25, 32), width=3)

    page.text((60, 205), cliente.nome, 28, True)
    page.text((60, 245), "Endereço de cobrança", 17, True, CINZA)
    linhas = claro_lines(cliente.endereco)
    caixa = page.block((60, 275), linhas, 22, espaco=12)

    page.rectangle((720, 215, 1180, 480), outline=(180, 180, 180))
    label_value(page, (740, 228), "Nº DO CONTRATO", random_digits(rng, 10))
    label_value(page, (740, 298), "VENCIMENTO", random_date(rng))
    label_value(page, (740, 368), "TOTAL DA FATURA (R$)", money(rng, 60, 420))

    page.text((60, 520), "RESUMO POR SERVIÇO", 20, True, (215, 25, 32))
    colunas = [("Descrição", 70), ("Período", 640), ("Valor (R$)", 1000)]
    linhas_tabela = [
        ["Claro Residencial - Internet", "01/10 a 31/10", money(rng, 80, 220)],
        ["Claro TV", "01/10 a 31/10", money(rng, 50, 180)],
        ["Claro Móvel", "01/10 a 31/10", money(rng, 40, 140)],
        ["Serviços adicionais", "", money(rng, 0, 30)],
        ["Impostos", "", money(rng, 10, 70)],
    ]
    draw_table(page, 560, colunas, linhas_tabela, (215, 25, 32))

    loja = generate_address(rng)
    page.text((60, 960), "PAGUE EM LOJAS CLARO", 18, True, CINZA)
    page.block((60, 995), two_line_address(loja), 22, espaco=10)

    draw_barcode(page, rng, 1250)

    sede = generate_address(rng)
    page.text((60, 1500), "Claro S.A. - CNPJ 00.000.000/0001-00", 20, True)
    page.block((60, 1535), two_line_address(sede), 20, espaco=8)
    page.text((60, 1615), "Central de atendimento 0800 000 0000", 20)
    draw_synthetic_mark(page)

    return RenderedDocument(
        image=page.image,
        linhas_endereco=linhas,
        regiao_endereco=relative_box(ROI_CLARO),
        caixa_texto_endereco=caixa,
        enderecos_distratores=[single_line_address(loja), single_line_address(sede)],
    )


RENDERERS = {
    "enel": render_enel,
    "sabesp": render_sabesp,
    "claro": render_claro,
}
