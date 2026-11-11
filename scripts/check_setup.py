"""Verifica se o ambiente está pronto: bibliotecas, Tesseract e um OCR de teste.

Uso:
    python scripts/check_setup.py
    python scripts/check_setup.py --lang eng
"""

import argparse
import sys
from importlib.metadata import version
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

falhas = 0


def ok(mensagem):
    print(f"[OK]    {mensagem}")


def falha(mensagem):
    global falhas
    falhas += 1
    print(f"[FALHA] {mensagem}")


def verificar_bibliotecas():
    try:
        import cv2
        import numpy
        import PIL
        import pytesseract

        ok(f"Python {sys.version.split()[0]}")
        ok(f"OpenCV {cv2.__version__}")
        ok(f"NumPy {numpy.__version__}")
        ok(f"Pillow {PIL.__version__}")
        ok(f"pytesseract {version('pytesseract')}")
        return True
    except ImportError as erro:
        falha(f"Biblioteca ausente: {erro.name}. Rode: pip install -r requirements.txt")
        return False


def verificar_tesseract(idioma):
    from citizentech_vision import ocr_setup

    try:
        caminho = ocr_setup.configure_tesseract()
    except RuntimeError as erro:
        falha(str(erro))
        return False

    ok(f"Tesseract {ocr_setup.tesseract_version()} em {caminho}")

    idiomas = ocr_setup.available_languages()
    if idioma not in idiomas:
        falha(
            f"Idioma '{idioma}' não instalado (disponíveis: {', '.join(idiomas)}). "
            "No Windows, reinstale marcando Portuguese; no Linux: "
            "apt install tesseract-ocr-por"
        )
        return False

    ok(f"Idioma '{idioma}' disponível")
    return True


def ocr_de_teste(idioma):
    import cv2
    import numpy as np
    import pytesseract

    texto_esperado = "AV PAULISTA 1578"
    imagem = np.full((120, 900, 3), 255, dtype=np.uint8)
    cv2.putText(
        imagem,
        texto_esperado,
        (20, 85),
        cv2.FONT_HERSHEY_SIMPLEX,
        2,
        (0, 0, 0),
        4,
    )

    lido = pytesseract.image_to_string(imagem, lang=idioma).strip()
    if "PAULISTA" in lido.upper():
        ok(f"OCR de teste leu: {lido!r}")
    else:
        falha(f"OCR de teste não reconheceu o texto (leu {lido!r})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", default="por", help="idioma do Tesseract (padrão: por)")
    args = parser.parse_args()

    if verificar_bibliotecas() and verificar_tesseract(args.lang):
        ocr_de_teste(args.lang)

    print()
    if falhas:
        print(f"{falhas} problema(s) encontrado(s).")
        sys.exit(1)
    print("Ambiente pronto.")


if __name__ == "__main__":
    main()
