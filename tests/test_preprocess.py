import cv2
import numpy as np
import pytest

from citizentech_vision.preprocess import (
    PASSOS,
    VARIANTES,
    apply_variant,
    binarize_adaptive,
    binarize_otsu,
    contrast_level,
    crop_relative,
    denoise_median,
    equalize,
    is_low_contrast,
    remove_specks,
    stretch_contrast,
    stretch_if_low_contrast,
    to_gray,
    upscale,
)


def imagem_texto(fundo=255, cor=0, tamanho=(120, 600)):
    imagem = np.full((*tamanho, 3), fundo, dtype=np.uint8)
    cv2.putText(imagem, "RUA TESTE 123", (15, 80), cv2.FONT_HERSHEY_SIMPLEX, 2, (cor,) * 3, 4)
    return imagem


def test_crop_relative_recorta_pela_proporcao():
    imagem = np.zeros((200, 400, 3), dtype=np.uint8)

    recorte = crop_relative(imagem, (0.25, 0.5, 0.75, 1.0))

    assert recorte.shape[:2] == (100, 200)


def test_to_gray_aceita_cor_e_cinza():
    colorida = imagem_texto()

    cinza = to_gray(colorida)

    assert cinza.ndim == 2
    assert to_gray(cinza) is cinza


def test_contraste_baixo_detectado():
    nitida = to_gray(imagem_texto())
    apagada = to_gray(imagem_texto(fundo=130, cor=100))

    assert not is_low_contrast(nitida)
    assert is_low_contrast(apagada)
    assert contrast_level(nitida) > contrast_level(apagada)


def test_equalizar_aumenta_contraste_de_imagem_apagada():
    apagada = to_gray(imagem_texto(fundo=130, cor=100))

    assert contrast_level(equalize(apagada)) > contrast_level(apagada)


def test_esticar_contraste_amplia_a_faixa_de_valores():
    apagada = to_gray(imagem_texto(fundo=130, cor=100))

    esticada = stretch_contrast(apagada)

    assert contrast_level(esticada) > 200
    assert not is_low_contrast(esticada)


def test_esticar_se_baixo_so_age_com_baixo_contraste():
    nitida = to_gray(imagem_texto())
    apagada = to_gray(imagem_texto(fundo=130, cor=100))

    assert np.array_equal(stretch_if_low_contrast(nitida), nitida)
    assert not np.array_equal(stretch_if_low_contrast(apagada), apagada)


def test_esticar_imagem_uniforme_nao_quebra():
    uniforme = np.full((40, 40), 120, dtype=np.uint8)

    assert np.array_equal(stretch_contrast(uniforme), uniforme)


def test_binarizacao_gera_apenas_preto_e_branco():
    cinza = to_gray(imagem_texto())

    for binaria in (binarize_otsu(cinza), binarize_adaptive(cinza)):
        assert set(np.unique(binaria)) <= {0, 255}
        assert binaria.shape == cinza.shape


def test_otsu_separa_texto_do_fundo():
    binaria = binarize_otsu(to_gray(imagem_texto()))

    assert (binaria == 0).mean() < 0.3
    assert (binaria == 255).mean() > 0.7


def test_ampliar_multiplica_dimensoes():
    imagem = np.zeros((50, 80), dtype=np.uint8)

    assert upscale(imagem, 2.0).shape == (100, 160)


def test_mediana_remove_ruido_sal_e_pimenta():
    rng = np.random.default_rng(0)
    base = np.full((100, 100), 200, dtype=np.uint8)
    ruidosa = base.copy()
    pontos = rng.integers(0, 100, size=(60, 2))
    ruidosa[pontos[:, 0], pontos[:, 1]] = 0

    limpa = denoise_median(ruidosa)

    assert np.abs(limpa.astype(int) - base).mean() < np.abs(ruidosa.astype(int) - base).mean()


def test_abertura_remove_pontos_isolados_e_mantem_traco_grosso():
    binaria = np.full((60, 60), 255, dtype=np.uint8)
    binaria[10, 10] = 0
    binaria[30:50, 20:26] = 0

    limpa = remove_specks(binaria)

    assert limpa[10, 10] == 255
    assert (limpa[30:50, 20:26] == 0).all()


def test_todas_as_variantes_usam_passos_existentes_e_rodam():
    imagem = imagem_texto()

    for nome, passos in VARIANTES.items():
        assert all(p in PASSOS for p in passos), nome
        resultado = apply_variant(imagem, nome)
        assert resultado.dtype == np.uint8, nome
        assert resultado.size > 0, nome


def test_variante_original_nao_altera_a_imagem():
    imagem = imagem_texto()

    assert apply_variant(imagem, "original") is imagem


def test_variante_com_otsu_devolve_imagem_binaria():
    binaria = apply_variant(imagem_texto(), "esticar+mediana+otsu")

    assert binaria.ndim == 2
    assert set(np.unique(binaria)) <= {0, 255}
