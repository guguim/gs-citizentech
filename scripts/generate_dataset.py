import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from citizentech_vision.synthetic.generator import DEFAULT_SEED, build_dataset


def main():
    parser = argparse.ArgumentParser(description="Gera o dataset sintético de comprovantes com gabarito")
    parser.add_argument("--output", type=Path, default=RAIZ / "data")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--docs-per-company", type=int, default=4)
    args = parser.parse_args()

    entradas = build_dataset(args.output, args.docs_per_company, seed=args.seed)
    print(f"{len(entradas)} fotos geradas em {args.output}")


if __name__ == "__main__":
    main()
