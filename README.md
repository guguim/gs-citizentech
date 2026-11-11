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
  synthetic/              gerador do dataset sintético
scripts/                  utilitários (verificação do ambiente, geração do dataset)
tests/                    testes automatizados
data/                     dataset sintético e gabarito
```

## Dataset sintético

Para testar o pipeline sem usar dados pessoais reais, o repositório traz um dataset sintético com gabarito, gerado por código:

- 3 empresas (Enel, Sabesp e Claro), com 4 documentos fictícios cada
- cada documento é fotografado de forma simulada em 3 condições: `frontal`, `inclinada` e `dificil` (perspectiva, rotação, sombra, pouca luz, desfoque e ruído), totalizando 36 fotos
- todos os nomes, endereços e números são inventados, e cada página traz a marca "DOCUMENTO SINTÉTICO PARA TESTES"
- cada comprovante tem o endereço do cliente e dois endereços "distratores" (agência ou loja de atendimento e sede da empresa)

Estrutura gerada:

```
data/synthetic/documents/    comprovantes limpos (PNG)
data/synthetic/photos/       fotos simuladas (JPG)
data/ground_truth/ground_truth.json   gabarito de cada foto
```

O gabarito traz, para cada foto: empresa, endereço correto separado em campos, linhas impressas, região do endereço (coordenadas relativas), endereços distratores, os 4 cantos do documento na foto e os parâmetros de perturbação usados.

Para gerar novamente (a semente fixa garante o mesmo resultado):

```bash
python scripts/generate_dataset.py
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
