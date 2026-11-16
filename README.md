# ZelaAí · Visão Computacional

Componente de **Visão Computacional** (Applied Computer Vision) do **ZelaAí**, plataforma de zeladoria urbana acessível desenvolvida para a **FIAP Global Solution 2026.2: CitizenTech**.

O serviço extrai automaticamente o endereço do cliente a partir da fotografia de uma conta de três empresas (Enel, Sabesp e Claro), para que o cidadão preencha o cadastro do ZelaAí em poucos segundos e confirme os dados lidos. Ele é consumido pela [API do ZelaAí](https://github.com/Rodriguessz/zelai-api) por HTTP, conforme descrito em [Integração com o ZelaAí](#integração-com-o-zelaaí).

## Ficha Técnica do MVP

| Item | Descrição |
|---|---|
| Nome do produto | ZelaAí |
| Cidadão e território | Idosos e pessoas com deficiência em bairros de São Paulo, os primeiros a sofrer com calçadas quebradas, semáforos sem funcionar e pontos de ônibus sem acessibilidade |
| Problema, em uma frase | Falhas no espaço público que afetam quem mais depende dele não chegam à prefeitura de forma simples e não são acompanhadas até a solução |
| Proposta de valor | *"Reporte em 1 minuto, acompanhe até resolver"*: o cidadão registra o problema, a IA prioriza, o gestor aprova e um robô protocola no Portal 156. A Visão Computacional agiliza o cadastro: a foto de uma conta preenche bairro, CEP e cidade, que o cidadão só confirma |
| Arquitetura: componentes | API Node.js 22 (Azure App Service) · PostgreSQL 16 · Key Vault · Application Insights · **Visão Computacional (serviço Python com OpenCV e Tesseract, este repositório)** · GenAI (triagem) · Apache Airflow (dados) · robô UiPath (RPA) · Power BI · front-end web acessível |
| Fontes de dados | Documentos sintéticos gerados pela equipe, com gabarito (sem dados pessoais reais) · ocorrências registradas na plataforma · dados abertos SP156 e GeoSampa · IBGE |
| Modelos de IA utilizados | OCR com Tesseract (idioma português) sobre imagens tratadas com OpenCV · LLM para triagem (GenAI), com plano B por regras e decisão final humana |
| URL do MVP e repositório | API: https://zelai-api.azurewebsites.net · Swagger: https://zelai-api.azurewebsites.net/docs · Repositório da API: https://github.com/Rodriguessz/zelai-api |
| Indicadores de impacto | Da Visão: acerto do endereço completo, taxa de revisão e tempo de leitura (ver [Avaliação](#avaliação)). Da plataforma: tempo médio entre registro e protocolo no 156, % de ocorrências resolvidas e prioridade por bairro |
| ODS conectados | ODS 9 (infraestrutura resiliente) · ODS 10 (redução das desigualdades: acessibilidade para idosos e PcD) · ODS 11 (cidades e comunidades sustentáveis) |

## Componente de Visão Computacional

Pipeline previsto:

1. Identificar o documento na fotografia
2. Corrigir a perspectiva
3. Pré-processar a imagem
4. Extrair o endereço por OCR, distinguindo-o dos demais endereços da fatura
5. Validar os dados e apresentá-los para confirmação ou correção
6. Entregar o endereço ao ZelaAí pela API HTTP, que mostra a sugestão ao cidadão para confirmação ou correção

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
  api.py                  serviço HTTP (FastAPI) que o ZelaAí consome
  demo/                   página de confirmação e correção do endereço (modo demonstração)
  textmatch.py            comparação aproximada de textos
  cities.py               lista de cidades conhecidas para corrigir o OCR
  metrics.py              métricas de avaliação (detecção e OCR)
  synthetic/              gerador do dataset sintético
scripts/                  utilitários (verificação do ambiente, geração do dataset, avaliação)
Dockerfile                imagem do serviço, com Tesseract e idioma português
tests/                    testes automatizados
data/                     dataset sintético e gabarito
```

## Integração com o ZelaAí

A API do ZelaAí (Node.js) chama este serviço por HTTP quando o cidadão envia a foto de uma conta em `POST /enderecos/extracao`. O serviço devolve uma **sugestão**: o cidadão confirma ou corrige em `PUT /enderecos/meu`, e a API grava apenas bairro, CEP e cidade (minimização de dados da LGPD).

```
Cidadão → ZelaAí API (POST /enderecos/extracao, campo "comprovante")
              └→ Visão (POST /extrair-endereco, campo "imagem")
                     rectify → empresa → zona → OCR → campos → validação → confiança
              ←─ { empresa, confianca, endereco }
Cidadão confirma → PUT /enderecos/meu
```

### Contrato

`POST /extrair-endereco`, `multipart/form-data`, campo `imagem` (JPG, PNG ou WEBP, até 5 MB). Se a variável `VISAO_API_KEY` estiver definida no serviço, a requisição precisa do header `x-api-key` com o mesmo valor.

```json
{
  "empresa": "Sabesp",
  "confianca": 0.93,
  "endereco": {
    "logradouro": "Alameda Voluntários da Pátria",
    "numero": "742",
    "bairro": "Parque São Jorge",
    "cep": "02633-675",
    "cidade": "São Paulo",
    "complemento": "Casa 149",
    "uf": "SP"
  },
  "revisar": false,
  "campos_revisar": [],
  "problemas": [],
  "metodo": "zona"
}
```

`empresa`, `confianca` e os cinco primeiros campos de `endereco` são os que a API do ZelaAí valida. Os demais são extras que a API atual descarta ao validar a resposta; ficam disponíveis caso ela passe a repassá-los ao front-end para destacar o que o cidadão precisa conferir. Campos não lidos vêm como `null`, e `confianca` fica sempre entre 0 e 1. A API do ZelaAí marca `revisar: true` quando `confianca < 0,8`, o mesmo limiar que usamos internamente.

| Código | Quando | O que o ZelaAí faz |
|---|---|---|
| 200 | endereço extraído (mesmo com baixa confiança) | mostra a sugestão para o cidadão confirmar |
| 401 | `x-api-key` ausente ou incorreta | plano B |
| 413 | imagem acima de 5 MB | plano B |
| 415 | arquivo que não é JPG, PNG ou WEBP | plano B |
| 422 | imagem ilegível ou nenhum endereço de cliente encontrado | plano B |

No plano B a API responde `fonte: "manual"` e orienta o cidadão a preencher o endereço à mão, então qualquer falha da Visão nunca trava o cadastro. A foto é processada em memória e **nunca é gravada em disco**.

### Variáveis de ambiente

| Onde | Variável | Uso |
|---|---|---|
| Serviço de Visão | `VISAO_API_KEY` | chave esperada no header `x-api-key` (vazia desativa a verificação, só para uso local) |
| Serviço de Visão | `VISAO_DEMO` | `1` liga a página de demonstração em `/demo/` (desligada por padrão, não use em produção) |
| Serviço de Visão | `PORT` | porta do servidor (padrão 8000 na imagem Docker) |
| Serviço de Visão | `TESSERACT_CMD` | caminho do Tesseract, se não estiver no PATH |
| API do ZelaAí | `VISAO_URL` | endereço base do serviço, sem a barra final |
| API do ZelaAí | `VISAO_API_KEY` | mesma chave do serviço, guardada no Key Vault |
| API do ZelaAí | `VISAO_TIMEOUT_MS` | tempo limite (padrão 15000). A leitura leva em média 1,4 s e chega a cerca de 2,3 s nas fotos difíceis |

### Como rodar o serviço

Localmente:

```bash
uvicorn citizentech_vision.api:app --port 8000
```

A documentação interativa fica em `http://localhost:8000/docs` e a checagem de saúde em `GET /health`. Para testar com uma foto do dataset:

```bash
curl -F "imagem=@data/synthetic/photos/sabesp_01_frontal.jpg" http://localhost:8000/extrair-endereco
```

Com Docker (Tesseract e português já incluídos):

```bash
docker build -t zelai-visao .
docker run -p 8000:8000 -e VISAO_API_KEY=troque-esta-chave zelai-visao
```

### Tela de confirmação e correção

O serviço inclui uma página de demonstração do fluxo que o cidadão percorre no ZelaAí. Ela fica desligada por padrão e é ativada com `VISAO_DEMO=1`:

```bash
VISAO_DEMO=1 uvicorn citizentech_vision.api:app --port 8000
```

Em PowerShell: `$env:VISAO_DEMO="1"; uvicorn citizentech_vision.api:app --port 8000`. Depois, abra `http://localhost:8000/`.

1. O cidadão envia a foto da conta (ou escolhe digitar o endereço).
2. O formulário aparece preenchido com a leitura. Os campos incertos ficam destacados com a mensagem "Confira este campo", sem depender só de cor, e a confiança é exibida em porcentagem.
3. Ele corrige o que for preciso. Se a leitura falhar, o formulário abre vazio para digitação manual (o mesmo plano B da API).
4. Ao confirmar, a página mostra o que seria salvo (`PUT /enderecos/meu` com bairro, CEP e cidade) e que a foto e os demais campos não são guardados.

A página usa rótulos associados aos campos, alvos de toque grandes, foco visível, mensagens de erro anunciadas por leitores de tela e respeita o tema claro ou escuro do aparelho. A rota `/demo/extrair` existe só nesse modo e não exige a chave de API, por isso a demonstração não deve ser publicada em produção. A rota oficial `/extrair-endereco` continua protegida.

### Publicação na Azure

O App Service Node da API não tem Tesseract, então a Visão roda como um **segundo serviço em contêiner** (por exemplo, um Web App for Containers ou um Container App), no mesmo grupo de recursos. Passos:

1. Publicar a imagem em um registro (por exemplo, Azure Container Registry) e criar o serviço apontando para ela, com `WEBSITES_PORT=8000` e health check em `/health`.
2. Guardar `VISAO_API_KEY` no Key Vault, com referência nas configurações do serviço, como já é feito com os demais segredos.
3. Na API do ZelaAí, definir `VISAO_URL` com a URL do serviço e `VISAO_API_KEY` com a mesma chave.

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

Os testes do serviço HTTP (`tests/test_api.py`) conferem a resposta contra o mesmo formato que a API do ZelaAí valida, as regras de chave, tipo e tamanho do arquivo e que nada é gravado em disco.
