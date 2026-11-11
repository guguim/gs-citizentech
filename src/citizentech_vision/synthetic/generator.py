import json
import random
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from .fake_data import generate_customer
from .layouts import RENDERERS
from .photo import CONDITIONS, render_photo, sample_params

DEFAULT_SEED = 2026


def build_dataset(destino, documentos_por_empresa=4, condicoes=tuple(CONDITIONS), seed=DEFAULT_SEED):
    destino = Path(destino)
    pasta_documentos = destino / "synthetic" / "documents"
    pasta_fotos = destino / "synthetic" / "photos"
    pasta_gabarito = destino / "ground_truth"
    for pasta in (pasta_documentos, pasta_fotos, pasta_gabarito):
        pasta.mkdir(parents=True, exist_ok=True)

    entradas = []
    for empresa, renderizar in RENDERERS.items():
        for numero in range(1, documentos_por_empresa + 1):
            rng_documento = random.Random(f"{seed}-{empresa}-{numero}")
            cliente = generate_customer(rng_documento)
            documento = renderizar(cliente, rng_documento)

            nome_documento = f"{empresa}_{numero:02d}"
            caminho_documento = pasta_documentos / f"{nome_documento}.png"
            documento.image.save(caminho_documento)
            documento_bgr = cv2.cvtColor(np.array(documento.image), cv2.COLOR_RGB2BGR)

            for condicao in condicoes:
                rng_foto = random.Random(f"{seed}-{empresa}-{numero}-{condicao}")
                params = sample_params(condicao, rng_foto)
                foto, cantos = render_photo(documento_bgr, params, rng_foto)

                caminho_foto = pasta_fotos / f"{nome_documento}_{condicao}.jpg"
                cv2.imwrite(str(caminho_foto), foto, [cv2.IMWRITE_JPEG_QUALITY, params.qualidade_jpeg])

                entradas.append(
                    {
                        "id": f"{nome_documento}_{condicao}",
                        "empresa": empresa,
                        "documento_limpo": caminho_documento.relative_to(destino).as_posix(),
                        "foto": caminho_foto.relative_to(destino).as_posix(),
                        "cliente": cliente.nome,
                        "endereco": asdict(cliente.endereco),
                        "linhas_impressas": documento.linhas_endereco,
                        "regiao_endereco": list(documento.regiao_endereco),
                        "enderecos_distratores": documento.enderecos_distratores,
                        "cantos_documento_foto": [[round(float(x), 1), round(float(y), 1)] for x, y in cantos],
                        "condicao": condicao,
                        "perturbacoes": asdict(params),
                    }
                )

    caminho_gabarito = pasta_gabarito / "ground_truth.json"
    caminho_gabarito.write_text(json.dumps(entradas, ensure_ascii=False, indent=2), encoding="utf-8")
    return entradas
