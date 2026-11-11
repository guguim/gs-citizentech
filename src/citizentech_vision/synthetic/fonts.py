from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

REGULAR = [
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/Library/Fonts/Arial.ttf",
]

BOLD = [
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def first_existing(candidatos):
    for caminho in candidatos:
        if Path(caminho).is_file():
            return caminho
    return None


@lru_cache(maxsize=None)
def load_font(tamanho, negrito=False):
    caminho = first_existing(BOLD if negrito else REGULAR)
    if caminho:
        return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default(tamanho)
