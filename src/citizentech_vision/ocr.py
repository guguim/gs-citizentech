import pytesseract

from .ocr_setup import configure_tesseract

IDIOMA_PADRAO = "por"
PSM_PADRAO = 6


def read_text(imagem, idioma=IDIOMA_PADRAO, psm=PSM_PADRAO):
    configure_tesseract()
    return pytesseract.image_to_string(imagem, lang=idioma, config=f"--psm {psm}").strip()
