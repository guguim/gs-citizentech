# gs-citizentech

MVP desenvolvido para o desafio **FIAP Global Solution 2026.2: CitizenTech**.

Este repositório reúne o componente de **Visão Computacional** (Applied Computer Vision): a extração automática de endereços a partir de fotografias de comprovantes de três empresas (Enel, Sabesp e Claro), para preencher o cadastro do MVP.

## Ficha Técnica do MVP

| Item | Descrição |
|---|---|
| Nome do produto | A definir pela equipe |
| Cidadão e território | A definir pela equipe |
| Problema, em uma frase | A definir pela equipe |
| Proposta de valor | A definir pela equipe |
| Arquitetura: componentes | A definir pela equipe |
| Fontes de dados | Documentos sintéticos gerados pela equipe, com gabarito (sem dados pessoais reais) |
| Modelos de IA utilizados | OCR com Tesseract (idioma português) |
| URL do MVP e repositório | A definir pela equipe |
| Indicadores de impacto | A definir pela equipe |
| ODS conectados | A definir pela equipe |

## Componente de Visão Computacional

Pipeline previsto:

1. Identificar o documento na fotografia
2. Corrigir a perspectiva
3. Pré-processar a imagem
4. Extrair o endereço por OCR, distinguindo-o dos demais endereços da fatura
5. Validar os dados e apresentá-los para confirmação ou correção
6. Entregar o endereço ao MVP

## Estrutura do projeto

```
src/citizentech_vision/   código do componente
scripts/                  utilitários (ex.: verificação do ambiente)
tests/                    testes automatizados
```

## Como instalar

Requisitos: Python 3.10 ou superior e Tesseract OCR com o idioma português.

1. Crie e ative o ambiente virtual.

   Windows (PowerShell):
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   Linux ou macOS:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Instale o Tesseract OCR:
   - **Windows:** baixe o instalador da UB Mannheim (https://github.com/UB-Mannheim/tesseract/wiki) e, durante a instalação, marque o idioma **Portuguese** em "Additional language data". Se o executável não ficar no PATH, defina a variável `TESSERACT_CMD` com o caminho (por exemplo, `C:\Program Files\Tesseract-OCR\tesseract.exe`).
   - **Linux (Debian/Ubuntu):** `sudo apt install tesseract-ocr tesseract-ocr-por`

4. Verifique se tudo está pronto:
   ```bash
   python scripts/check_setup.py
   ```

## Como testar

```bash
pytest
```
