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
  ocr.py                  leitura de texto e palavras com Tesseract
  company.py              identificação da empresa pelo cabeçalho
  companies.py            configuração por empresa (zona do endereço, palavras-chave)
  address.py              separação do endereço em campos
  validation.py           validação dos campos e consistência CEP x UF
  voting.py               votação entre variantes de pré-processamento
  extraction.py           pipeline de extração do endereço do cliente
  textmatch.py            comparação aproximada de textos
  cities.py               lista de cidades conhecidas para corrigir o OCR
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

## Extração do endereço do cliente

A função `extract_address(foto)` (`src/citizentech_vision/extraction.py`) recebe a foto e devolve o endereço separado em campos, com confiança e a lista de campos que o usuário deve conferir. Para testar em uma foto:

```bash
python scripts/extract_address.py data/synthetic/photos/enel_01_frontal.jpg
```

### Como funciona

1. **Retificação:** a página é localizada e corrigida (seção anterior).
2. **Empresa:** o cabeçalho (14% superior da página) é lido com OCR e comparado com palavras-chave de cada empresa (`ENEL`, `SABESP`, `CLARO` e termos como `SANEAMENTO` e `FATURA DE SERVIÇOS`). A comparação aceita pequenos erros de OCR, como `Sa besp`.
3. **Zona do endereço:** cada empresa tem uma região configurada em `companies.py` onde fica o endereço do cliente. O recorte passa por `prepare_for_ocr` e é lido linha a linha. Agências, lojas de pagamento e sede ficam fora dessa região, e é assim que o endereço do cliente é distinguido dos demais.
4. **Plano B por âncora:** se a empresa não foi identificada ou o resultado da zona não passa na validação, a página inteira é lida e o endereço é procurado logo abaixo de um rótulo como `ENDEREÇO DO IMÓVEL` ou `ENDEREÇO DE COBRANÇA`. Linhas depois de rótulos como `AGÊNCIA`, `LOJAS` e `SEDE` encerram o bloco. Sem rótulo, o método aceita só um bloco com CEP na parte superior da página (até 45% da altura).
5. **Separação em campos:** o parser entende os três formatos (Enel em maiúsculas com bairro em linha própria, Sabesp abreviada em duas linhas, Claro com bairro e cidade na mesma linha), expande abreviações (`AV` vira `Avenida`, `CS 143` vira `Casa 143`), tolera separadores trocados pelo OCR e corrige a cidade com uma lista de cidades conhecidas.
6. **Validação:** campos obrigatórios (logradouro, número, cidade, UF e CEP), formato do CEP, UF existente, CEP dentro da faixa da UF, número com formato plausível e termos suspeitos no logradouro e no bairro (por exemplo, palavra de uma ou duas letras ou começando em minúscula). Se a UF não for lida, ela é inferida do CEP e marcada para revisão.
7. **Reforço:** quando a primeira leitura tem problema ou baixa confiança, o recorte é lido de novo com mais duas variantes de pré-processamento (`mediana` e `cinza`) e cada campo é decidido por maioria. Se as variantes divergem, o campo é marcado para revisão.
8. **Confiança e revisão:** a confiança é a média da confiança do Tesseract nas linhas usadas, menos 0,15 por problema encontrado. Campos com palavra de baixa confiança, divergência ou falha na validação vão em `campos_revisar`. Todos os campos são apresentados para confirmação, e os listados em `campos_revisar` devem ser destacados.

O resultado (`ExtractionResult`) traz `encontrado`, `empresa`, `campos`, `confianca`, `precisa_revisao`, `campos_revisar`, `problemas`, `metodo` e as linhas lidas.

### Avaliação

```bash
python scripts/evaluate_extraction.py
python scripts/evaluate_extraction.py --metodo zona
python scripts/evaluate_extraction.py --metodo ancora
python scripts/evaluate_extraction.py --condicao dificil --saida data/output/extracao.json
```

O script compara cada campo com o gabarito (ignorando maiúsculas e espaços, mas não acentos) nas 36 fotos. A coluna "endereço" é a porcentagem de fotos com os sete campos corretos; "distrator" é a porcentagem de fotos em que o CEP extraído é o de uma agência, loja ou sede.

| Método | Frontal | Inclinada | Difícil | Geral | Empresa | Distrator | Tempo por foto |
|---|---|---|---|---|---|---|---|
| Zona por empresa | 100% | 100% | 67% | 89% | 100% | 0% | 0,7 s |
| Âncora (página inteira) | 100% | 92% | 50% | 81% | 100% | 0% | 1,7 s |
| **Automático (zona, depois âncora)** | 100% | 100% | 67% | **89%** | 100% | 0% | 1,4 s |

Acerto por campo no modo automático: logradouro 89%, número 97%, complemento 94%, bairro 97%, cidade 97%, UF 97% e CEP 97%.

Confiança e revisão no modo automático:

- 14 das 36 fotos (39%) foram marcadas para revisão.
- As 4 fotos com algum campo errado foram todas marcadas para revisão. Das 32 corretas, 10 também foram marcadas, ou seja, o sistema é conservador.
- A confiança média é 0,72 nas fotos corretas e 0,23 nas erradas.

### Análise dos erros

Os quatro erros do modo automático são todos de foto difícil (escura, com sombra, desfoque e ruído):

| Foto | O que aconteceu |
|---|---|
| `enel_02_dificil` | `Dom Pedro II` lido como `Dom Pedro Tt`. O termo de duas letras é apontado como suspeito. |
| `sabesp_02_dificil` | A foto é ilegível (escura, borrada e com a página 17 px deslocada na retificação). O sistema não inventa endereço, devolve confiança 0 e pede preenchimento manual. |
| `sabesp_03_dificil` | `José` sem acento e complemento `BL B AP 174` lido como `BL BAP 174`. O complemento é apontado como não reconhecido. |
| `claro_03_dificil` | `Itapetininga` lido como `Rapetininga` e `Barão` como `Bardo`. As variantes divergem e o campo é marcado para revisão. |

Um erro que o plano B por âncora cometia antes de uma correção: em `claro_04_dificil`, quando o rótulo do endereço do cliente não era lido, ele aceitava o primeiro CEP da página, e o seguinte era o de uma loja (um endereço distrator). Agora ele só aceita blocos na parte superior da página; sem rótulo e sem bloco, devolve "não encontrado" e pede preenchimento manual. Há um teste que cobre esse caso.

### Limitações

- As fotos são simuladas e os três layouts foram desenhados pela equipe com base em faturas reais, mas não são cópias. Em faturas reais, a zona do endereço de cada empresa, as palavras-chave e os rótulos precisam ser calibrados.
- Limiares como 0,7 de confiança por palavra e 45% da altura da página foram escolhidos olhando para este dataset, e os números acima tendem a ser otimistas.
- A lista de cidades conhecidas é parcial (capitais e cidades grandes). Em produção deve ser trocada pela base de municípios do IBGE. A validação CEP x UF usa as faixas gerais dos Correios, sem consultar uma base de CEPs, então não confere se a rua existe naquele CEP.
- O OCR confiante e errado é possível: nomes de rua lidos errado com palavras que parecem plausíveis (`Rapetininga`) só são pegos quando as variantes divergem.
- Perda de acentos (`José` lido como `Jose`) conta como erro na avaliação, mas é de baixo impacto para o usuário que confirma o endereço.

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
