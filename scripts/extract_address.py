import argparse
import json
import sys
from pathlib import Path

import cv2

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from citizentech_vision.extraction import METODOS, extract_address


def main():
    parser = argparse.ArgumentParser(description="Extrai o endereço do cliente de uma foto de fatura.")
    parser.add_argument("foto", type=Path)
    parser.add_argument("--metodo", choices=METODOS, default="auto")
    args = parser.parse_args()

    imagem = cv2.imread(str(args.foto))
    if imagem is None:
        sys.exit(f"Não foi possível abrir a imagem: {args.foto}")

    resultado = extract_address(imagem, metodo=args.metodo)
    saida = {
        "encontrado": resultado.encontrado,
        "empresa": resultado.empresa,
        "endereco": resultado.campos,
        "confianca": round(resultado.confianca, 2),
        "precisa_revisao": resultado.precisa_revisao,
        "campos_revisar": resultado.campos_revisar,
        "problemas": resultado.problemas,
        "metodo": resultado.metodo,
    }
    print(json.dumps(saida, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
