import cv2
import numpy as np
import pytest
import pytesseract

from citizentech_vision import ocr_setup


def test_find_tesseract_usa_variavel_de_ambiente(tmp_path, monkeypatch):
    falso = tmp_path / "tesseract"
    falso.write_text("")
    monkeypatch.setenv("TESSERACT_CMD", str(falso))

    assert ocr_setup.find_tesseract() == str(falso)


def test_configure_tesseract_falha_com_mensagem_clara(monkeypatch):
    monkeypatch.setattr(ocr_setup, "find_tesseract", lambda: None)

    with pytest.raises(RuntimeError, match="Tesseract não encontrado"):
        ocr_setup.configure_tesseract()


def test_ocr_le_texto_simples():
    if ocr_setup.find_tesseract() is None:
        pytest.skip("Tesseract não instalado")
    ocr_setup.configure_tesseract()

    idioma = "por" if "por" in ocr_setup.available_languages() else "eng"
    imagem = np.full((120, 900, 3), 255, dtype=np.uint8)
    cv2.putText(imagem, "AV PAULISTA 1578", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 4)

    texto = pytesseract.image_to_string(imagem, lang=idioma)

    assert "PAULISTA" in texto.upper()
