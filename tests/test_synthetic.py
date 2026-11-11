import json
import random
import re

import numpy as np
import pytest

from citizentech_vision.synthetic.fake_data import CITIES, generate_customer
from citizentech_vision.synthetic.generator import build_dataset
from citizentech_vision.synthetic.layouts import PAGE_SIZE, RENDERERS
from citizentech_vision.synthetic.photo import CANVAS_SIZE, CONDITIONS, render_photo, sample_params

PADRAO_CEP = re.compile(r"^\d{5}-\d{3}$")
UFS_VALIDAS = {cidade[1] for cidade in CITIES}


def test_cliente_e_deterministico_para_a_mesma_semente():
    assert generate_customer(random.Random(7)) == generate_customer(random.Random(7))


def test_endereco_gerado_tem_campos_validos():
    for semente in range(50):
        endereco = generate_customer(random.Random(semente)).endereco
        assert PADRAO_CEP.match(endereco.cep)
        assert endereco.uf in UFS_VALIDAS
        assert endereco.numero.isdigit()
        assert endereco.logradouro and endereco.bairro and endereco.cidade


@pytest.mark.parametrize("empresa", list(RENDERERS))
def test_layout_tem_tamanho_esperado_e_texto_dentro_da_regiao(empresa):
    rng = random.Random(3)
    for _ in range(30):
        documento = RENDERERS[empresa](generate_customer(rng), rng)
        largura, altura = PAGE_SIZE
        x0, y0, x1, y1 = documento.regiao_endereco
        caixa = documento.caixa_texto_endereco

        assert documento.image.size == PAGE_SIZE
        assert len(documento.enderecos_distratores) == 2
        assert caixa[0] >= x0 * largura and caixa[2] <= x1 * largura
        assert caixa[1] >= y0 * altura and caixa[3] <= y1 * altura


@pytest.mark.parametrize("condicao", list(CONDITIONS))
def test_foto_mantem_documento_dentro_da_imagem(condicao):
    rng = random.Random(11)
    documento = RENDERERS["enel"](generate_customer(rng), rng)
    bgr = np.array(documento.image)[:, :, ::-1].copy()

    params = sample_params(condicao, rng)
    foto, cantos = render_photo(bgr, params, rng)

    largura, altura = CANVAS_SIZE
    assert foto.shape == (altura, largura, 3)
    assert cantos.shape == (4, 2)
    assert cantos[:, 0].min() >= 0 and cantos[:, 0].max() <= largura
    assert cantos[:, 1].min() >= 0 and cantos[:, 1].max() <= altura


def test_dataset_gera_arquivos_e_gabarito_consistentes(tmp_path):
    entradas = build_dataset(tmp_path, documentos_por_empresa=1, condicoes=("frontal",))

    gabarito = json.loads((tmp_path / "ground_truth" / "ground_truth.json").read_text(encoding="utf-8"))
    assert len(gabarito) == len(entradas) == len(RENDERERS)
    assert {e["empresa"] for e in gabarito} == set(RENDERERS)

    for entrada in gabarito:
        assert (tmp_path / entrada["foto"]).is_file()
        assert (tmp_path / entrada["documento_limpo"]).is_file()
        assert PADRAO_CEP.match(entrada["endereco"]["cep"])
        assert len(entrada["cantos_documento_foto"]) == 4
        assert len(entrada["enderecos_distratores"]) == 2
        assert entrada["endereco"]["cep"] in " ".join(entrada["linhas_impressas"])


def test_dataset_e_reprodutivel(tmp_path):
    primeiro = build_dataset(tmp_path / "a", documentos_por_empresa=1, condicoes=("inclinada",))
    segundo = build_dataset(tmp_path / "b", documentos_por_empresa=1, condicoes=("inclinada",))

    assert primeiro == segundo
