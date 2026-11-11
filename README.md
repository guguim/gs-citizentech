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
  document.py             detecção do documento e correção de perspectiva
  preprocess.py           pré-processamento da imagem para OCR
  ocr.py                  leitura de texto com Tesseract
  metrics.py              métricas de avaliação (detecção e OCR)
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

## Detecção do documento e correção de perspectiva

A função `rectify_document` recebe a foto e devolve o documento em visão frontal, com tamanho fixo de página A4 (1240 x 1754 px):

1. Calcula o gradiente de cor da imagem (Sobel nos três canais) e binariza as bordas fortes
2. Fecha pequenas falhas com morfologia e pega o contorno externo
3. Aproxima o contorno por um quadrilátero (`approxPolyDP`) e ordena os cantos: superior esquerdo, superior direito, inferior direito, inferior esquerdo
4. Refina cada lado: procura a borda real ao longo da normal, ajusta uma reta por lado e recalcula os cantos pela interseção das retas
5. Aplica `getPerspectiveTransform` e `warpPerspective`

Se o limiar de Otsu for necessário como reserva, ele só entra quando o gradiente não encontra nenhum quadrilátero válido. Se nada é encontrado, a imagem original é devolvida com `encontrado=False`, para o MVP pedir outra foto ou a digitação manual.

A confiança (`confianca`) mede o quanto as bordas do quadrilátero são fortes e serve como filtro. Ela não é uma probabilidade calibrada.

Para avaliar nas 36 fotos do dataset:

```bash
python scripts/evaluate_document_detection.py
```

Resultado atual:

| Condição | Fotos | Documento encontrado | IoU médio | Erro médio nos cantos |
|---|---|---|---|---|
| frontal | 12 | 12 | 0,998 | 1,3 px |
| inclinada | 12 | 12 | 0,998 | 1,4 px |
| dificil | 12 | 12 | 0,997 | 2,6 px |

O tempo médio é de 0,2 s por foto. As imagens corrigidas ficam em `data/output/rectified/`.

Limitações: os testes usam fotos simuladas; o documento precisa estar em pé (orientação retrato) e inteiro na imagem; fundos com muitos objetos ou texturas fortes podem confundir a detecção.

## Pré-processamento e OCR

Depois da correção de perspectiva, o recorte da região do endereço passa por `prepare_for_ocr` e segue para `read_text` (`pytesseract`, `lang="por"`, `--psm 6`).

O pipeline escolhido é: tons de cinza, filtro de mediana 3x3 e limiar adaptativo gaussiano (bloco 51, constante 15). Ele foi escolhido comparando variantes uma a uma com `scripts/experiment_preprocessing.py`, que mede o erro do OCR contra o texto impresso conhecido (gabarito) nas 36 fotos já retificadas:

- **CER:** taxa de erro de caracteres (distância de edição dividida pelo tamanho do texto esperado). Menor é melhor.
- **CEP ok:** porcentagem de recortes em que o CEP esperado foi lido corretamente.

| Variante | CER frontal | CER inclinada | CER difícil | CER geral | CEP ok |
|---|---|---|---|---|---|
| referência: documento limpo, sem pré-processamento | 0,001 | 0,001 | 0,001 | 0,001 | 100% |
| original (sem pré-processamento) | 0,002 | 0,001 | 0,385 | 0,129 | 89% |
| cinza | 0,002 | 0,001 | 0,373 | 0,125 | 89% |
| ampliar 2x | 0,001 | 0,001 | 1,760 | 0,587 | 89% |
| mediana 3x3 | 0,002 | 0,002 | 0,207 | 0,070 | 89% |
| mediana 5x5 | 0,004 | 0,004 | 0,254 | 0,088 | 89% |
| equalizar histograma | 4,260 | 1,852 | 2,298 | 2,803 | 8% |
| esticar contraste | 0,002 | 0,001 | 0,391 | 0,131 | 89% |
| Otsu | 0,002 | 0,003 | 0,348 | 0,118 | 89% |
| mediana + Otsu | 0,006 | 0,005 | 0,267 | 0,093 | 86% |
| equalizar + mediana + Otsu | 2,773 | 1,533 | 1,704 | 2,003 | 3% |
| esticar + mediana + Otsu | 0,002 | 0,010 | 0,273 | 0,095 | 81% |
| **mediana + adaptativo (escolhida)** | 0,001 | 0,006 | **0,087** | **0,031** | **94%** |
| ampliar + mediana + adaptativo | 0,002 | 0,000 | 0,135 | 0,046 | 89% |
| esticar + mediana + adaptativo | 0,002 | 0,008 | 0,928 | 0,313 | 83% |
| esticar (só se baixo contraste) + mediana + adaptativo | 0,001 | 0,006 | 0,928 | 0,312 | 83% |
| mediana + adaptativo + abertura | 0,013 | 0,013 | 0,220 | 0,082 | 81% |
| mediana + adaptativo + fechamento | 0,006 | 0,014 | 0,092 | 0,037 | 89% |

O que os experimentos mostraram:

- Fotos frontais e inclinadas já são lidas quase sem erro sem pré-processamento. O ganho está nas fotos difíceis (escuras, com sombra, desfoque e ruído).
- O filtro de mediana 3x3 reduz o ruído sem apagar os caracteres. O de 5x5 já é pior.
- O limiar adaptativo, que calcula o limite em cada vizinhança, lida bem com a sombra, e o Otsu global não. O bloco e a constante foram ajustados no próprio dataset; em fotos reais podem precisar de reajuste.
- A equalização de histograma piora muito o resultado. O papel branco domina o histograma do recorte, e a equalização espalha as pequenas variações desse fundo por toda a faixa de cinzas, transformando-o em ruído.
- Esticar o contraste não ajuda sozinho e piora com o limiar adaptativo, provavelmente porque amplifica o ruído e a constante do limiar fica mal calibrada.
- Ampliar a imagem 2x não ajuda: o texto já tem tamanho suficiente (cerca de 30 px de altura) e a ampliação também aumenta o ruído.
- Abrir a máscara (erosão e dilatação) piora o resultado, provavelmente por apagar traços finos das letras; fechar não traz ganho.
- No `--psm`, os modos 6 (bloco de texto) e 11 (texto esparso) têm erro parecido e os modos 3 e 4 ficam um pouco piores. Os modos de linha única (7 e 13) falham porque o recorte tem três linhas. Foi usado o 6.

Erros que sobram na condição difícil:

- Em `sabesp_02_dificil`, a página retificada ficou 17 px deslocada na vertical. O recorte fixo corta a primeira linha, e o OCR devolve lixo. Isso mostra que o recorte por coordenadas fixas é frágil e deve ganhar margem ou âncoras.
- Em `claro_01_dificil`, o OCR leu um dígito errado do CEP (5 no lugar de 3). Esse tipo de erro só é pego na validação e na confirmação pelo usuário.
- Os acentos quase não contam: o CER sem acentos é praticamente igual ao CER geral.

Para repetir a comparação:

```bash
python scripts/experiment_preprocessing.py
python scripts/experiment_preprocessing.py --variante mediana mediana+adaptativo
python scripts/experiment_preprocessing.py --varrer-psm mediana+adaptativo
```

A execução completa leva alguns minutos e grava o detalhe por foto em `data/output/preprocessing_experiments.csv`.

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
