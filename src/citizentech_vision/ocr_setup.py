import os
import shutil
from pathlib import Path

import pytesseract

CAMINHO_PADRAO_WINDOWS = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")

MENSAGEM_NAO_ENCONTRADO = (
    "Tesseract não encontrado. Instale o Tesseract OCR (no Windows, use o "
    "instalador da UB Mannheim e marque o idioma Portuguese) ou defina a "
    "variável de ambiente TESSERACT_CMD com o caminho do executável."
)


def find_tesseract():
    do_ambiente = os.environ.get("TESSERACT_CMD")
    if do_ambiente and Path(do_ambiente).is_file():
        return do_ambiente

    do_path = shutil.which("tesseract")
    if do_path:
        return do_path

    if CAMINHO_PADRAO_WINDOWS.is_file():
        return str(CAMINHO_PADRAO_WINDOWS)

    return None


def configure_tesseract():
    caminho = find_tesseract()
    if caminho is None:
        raise RuntimeError(MENSAGEM_NAO_ENCONTRADO)
    pytesseract.pytesseract.tesseract_cmd = caminho
    return caminho


def available_languages():
    configure_tesseract()
    return pytesseract.get_languages(config="")


def tesseract_version():
    configure_tesseract()
    return str(pytesseract.get_tesseract_version())
