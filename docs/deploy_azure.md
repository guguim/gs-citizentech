# Publicação do serviço de Visão na Azure

Este guia coloca o serviço de Visão no ar como um segundo Web App (contêiner) ao lado da API do ZelaAí, reaproveitando o mesmo grupo de recursos e o mesmo plano Linux B1. A imagem é publicada automaticamente pelo workflow `Publish container image` a cada merge na `main`.

## 1. Imagem

```
ghcr.io/guguim/gs-citizentech:latest
```

O pacote nasce privado. Depois da primeira execução do workflow, em GitHub → Packages → `gs-citizentech` → Package settings, mude a visibilidade para **Public**, para que a Azure baixe a imagem sem credenciais.

## 2. Criar o Web App em contêiner

Os nomes abaixo seguem o `infra/azure-setup.sh` da API (`rg-citizentech-prod` e `plan-zelai-api`). O nome do Web App precisa ser único na Azure.

```bash
RG=rg-citizentech-prod
PLAN=plan-zelai-api
APP=zelai-visao

az webapp create -g $RG -p $PLAN -n $APP \
  --container-image-name ghcr.io/guguim/gs-citizentech:latest

az webapp config appsettings set -g $RG -n $APP --settings \
  WEBSITES_PORT=8000 \
  VISAO_API_KEY="<chave-forte>"

az webapp config set -g $RG -n $APP --generic-configurations '{"healthCheckPath": "/health"}'
```

A chave pode, como os demais segredos da API, ficar no Key Vault e ser referenciada com `@Microsoft.KeyVault(VaultName=<cofre>;SecretName=<segredo>)`.

## 3. Verificar o serviço

```bash
curl https://zelai-visao.azurewebsites.net/health
```

Resposta esperada: `{"status":"ok","servico":"visao-computacional"}`. O primeiro acesso pode demorar enquanto a Azure baixa a imagem.

Teste a rota protegida:

```bash
curl -X POST https://zelai-visao.azurewebsites.net/extrair-endereco \
  -H "x-api-key: <chave-forte>" \
  -F "imagem=@foto.jpg"
```

Sem o header, a resposta deve ser `401`.

## 4. Ligar a API do ZelaAí ao serviço

Na API (`zelai-api`), defina as duas variáveis e reinicie. A chave tem que ser exatamente a mesma do serviço de Visão.

```bash
az webapp config appsettings set -g rg-citizentech-prod -n zelai-api --settings \
  VISAO_URL="https://zelai-visao.azurewebsites.net" \
  VISAO_API_KEY="<chave-forte>"
```

Se a API usar Key Vault para os segredos, grave `VISAO_API_KEY` lá e use a referência, como nos demais. Depois de alterar a referência, reinicie o App Service, pois ele só consulta o cofre de novo quando uma configuração muda.

## 5. Atualizações

Cada merge na `main` do repositório de Visão publica uma imagem nova com as tags `latest` e o hash curto do commit. Para a Azure puxar a versão nova, reinicie o Web App (`az webapp restart -g rg-citizentech-prod -n zelai-visao`) ou habilite o webhook de implantação contínua do próprio Web App.

## Demonstração

Não defina `VISAO_DEMO` em produção. A variável liga a página de demonstração e uma rota sem chave de API, e serve apenas para testes locais.
