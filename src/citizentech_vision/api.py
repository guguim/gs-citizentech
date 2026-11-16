import hmac
import os
from pathlib import Path

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from citizentech_vision.extraction import extract_address

TAMANHO_MAXIMO_BYTES = 5 * 1024 * 1024
TIPOS_ACEITOS = ("image/jpeg", "image/png", "image/webp")
CAMPOS_CONTRATO = ("logradouro", "numero", "bairro", "cep", "cidade")
CAMPOS_EXTRAS = ("complemento", "uf")
NOMES_EMPRESAS = {"enel": "Enel", "sabesp": "Sabesp", "claro": "Claro"}
PASTA_DEMO = Path(__file__).resolve().parent / "demo"
VALORES_VERDADEIROS = ("1", "true", "sim", "yes")


def nome_da_empresa(empresa):
    if not empresa:
        return None
    return NOMES_EMPRESAS.get(empresa, empresa.title())


def valor_ou_nulo(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def build_response(resultado):
    campos = resultado.campos or {}
    endereco = {nome: valor_ou_nulo(campos.get(nome)) for nome in CAMPOS_CONTRATO}
    for nome in CAMPOS_EXTRAS:
        endereco[nome] = valor_ou_nulo(campos.get(nome))
    confianca = min(1.0, max(0.0, float(resultado.confianca)))
    return {
        "empresa": nome_da_empresa(resultado.empresa),
        "confianca": round(confianca, 4),
        "endereco": endereco,
        "revisar": bool(resultado.precisa_revisao),
        "campos_revisar": list(resultado.campos_revisar),
        "problemas": [str(problema) for problema in resultado.problemas],
        "metodo": resultado.metodo,
    }


def decode_image(conteudo):
    dados = np.frombuffer(conteudo, dtype=np.uint8)
    return cv2.imdecode(dados, cv2.IMREAD_COLOR)


def demo_ativado(demo):
    if demo is not None:
        return bool(demo)
    return os.environ.get("VISAO_DEMO", "").strip().lower() in VALORES_VERDADEIROS


def process_upload(imagem, extractor):
    if imagem.content_type not in TIPOS_ACEITOS:
        raise HTTPException(status_code=415, detail="Envie uma imagem JPG, PNG ou WEBP.")
    conteudo = imagem.file.read(TAMANHO_MAXIMO_BYTES + 1)
    if len(conteudo) > TAMANHO_MAXIMO_BYTES:
        raise HTTPException(status_code=413, detail="A imagem excede o limite de 5 MB.")
    foto = decode_image(conteudo)
    if foto is None:
        raise HTTPException(status_code=422, detail="Não foi possível abrir a imagem enviada.")
    resultado = extractor(foto)
    if not resultado.encontrado:
        raise HTTPException(status_code=422, detail="Nenhum endereço de cliente foi encontrado na imagem.")
    return build_response(resultado)


def create_app(api_key=None, extractor=extract_address, demo=None):
    chave_esperada = api_key if api_key is not None else os.environ.get("VISAO_API_KEY", "")
    app = FastAPI(
        title="ZelaAí · Visão Computacional",
        version="1.0.0",
        description="Extração automática do endereço do cliente a partir da foto de uma conta (Enel, Sabesp ou Claro).",
    )

    def exigir_chave(x_api_key: str = Header(default="")):
        if chave_esperada and not hmac.compare_digest(x_api_key, chave_esperada):
            raise HTTPException(status_code=401, detail="Chave de API inválida.")

    @app.get("/health")
    def health():
        return {"status": "ok", "servico": "visao-computacional"}

    @app.post("/extrair-endereco", dependencies=[Depends(exigir_chave)])
    def extrair_endereco(imagem: UploadFile = File(...)):
        return process_upload(imagem, extractor)

    if demo_ativado(demo):
        @app.post("/demo/extrair", include_in_schema=False)
        def extrair_demo(imagem: UploadFile = File(...)):
            return process_upload(imagem, extractor)

        @app.get("/", include_in_schema=False)
        def raiz():
            return RedirectResponse("/demo/")

        app.mount("/demo", StaticFiles(directory=PASTA_DEMO, html=True), name="demo")

    return app


app = create_app()
