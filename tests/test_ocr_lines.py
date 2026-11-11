from citizentech_vision.ocr import Palavra, group_lines


def palavra(texto, x, y, largura=60, altura=20, confianca=0.9, bloco=1, paragrafo=1, linha=1):
    return Palavra(texto, x, y, largura, altura, confianca, bloco, paragrafo, linha)


def test_agrupa_palavras_da_mesma_linha_em_ordem_horizontal():
    palavras = [palavra("RUA", 100, 50), palavra("A,", 40, 50), palavra("10", 170, 50)]

    linhas = group_lines(palavras)

    assert len(linhas) == 1
    assert linhas[0].texto == "A, RUA 10"
    assert linhas[0].x0 == 40
    assert linhas[0].x1 == 230


def test_linhas_saem_ordenadas_de_cima_para_baixo():
    palavras = [
        palavra("SEGUNDA", 40, 120, linha=2),
        palavra("PRIMEIRA", 40, 50, linha=1),
    ]

    assert [l.texto for l in group_lines(palavras)] == ["PRIMEIRA", "SEGUNDA"]


def test_separa_colunas_distantes_na_mesma_linha():
    palavras = [palavra("RUA", 40, 50), palavra("A", 110, 50), palavra("CLIENTE", 700, 50), palavra("123", 780, 50)]

    linhas = group_lines(palavras)

    assert [l.texto for l in linhas] == ["RUA A", "CLIENTE 123"]


def test_confianca_da_linha_e_a_media_das_palavras():
    palavras = [palavra("A", 40, 50, confianca=0.5), palavra("B", 110, 50, confianca=0.9)]

    assert group_lines(palavras)[0].confianca == 0.7
