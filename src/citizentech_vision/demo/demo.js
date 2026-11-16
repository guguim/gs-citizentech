const CAMPOS = ["cep", "numero", "logradouro", "complemento", "bairro", "cidade", "uf"];
const LIMITE_BYTES = 5 * 1024 * 1024;
const TIPOS = ["image/jpeg", "image/png", "image/webp"];
const LIMIAR_REVISAO = 0.8;

const el = (id) => document.getElementById(id);
const etapas = { envio: el("etapa-envio"), confirmacao: el("etapa-confirmacao"), final: el("etapa-final") };

let urlPrevia = null;

function mostrarEtapa(nome, foco) {
  Object.entries(etapas).forEach(([chave, secao]) => { secao.hidden = chave !== nome; });
  if (foco) { foco.focus(); window.scrollTo({ top: 0 }); }
}

function mensagemErro(id, texto) {
  const alvo = el(id);
  alvo.textContent = texto || "";
  alvo.hidden = !texto;
}

function formatarCep(valor) {
  const digitos = (valor || "").replace(/\D/g, "").slice(0, 8);
  return digitos.length > 5 ? `${digitos.slice(0, 5)}-${digitos.slice(5)}` : digitos;
}

function campoDe(nome) {
  return document.querySelector(`.campo[data-campo="${nome}"]`);
}

function marcarRevisao(nome, ativo) {
  const campo = campoDe(nome);
  campo.classList.toggle("revisar", ativo);
  campo.querySelector(".marca-revisao").hidden = !ativo;
}

function limparErros() {
  ["cep", "bairro", "cidade"].forEach((nome) => {
    mensagemErro(`erro-${nome}`, "");
    campoDe(nome).classList.remove("invalido");
  });
}

function preencherFormulario(endereco, camposRevisar) {
  CAMPOS.forEach((nome) => {
    const valor = endereco && endereco[nome] ? endereco[nome] : "";
    el(nome).value = nome === "cep" ? formatarCep(valor) : valor;
    marcarRevisao(nome, camposRevisar.includes(nome) || (!valor && nome !== "complemento" && camposRevisar.length > 0));
  });
  limparErros();
}

function mostrarResumo(dados) {
  const percentual = Math.round(dados.confianca * 100);
  const empresa = dados.empresa ? `Conta da ${dados.empresa}` : "Empresa não identificada";
  el("resumo-texto").textContent = `${empresa} · confiança da leitura: ${percentual}%`;
  el("barra-preenchida").style.width = `${percentual}%`;
  el("barra").classList.toggle("baixa", dados.confianca < LIMIAR_REVISAO);
  el("resumo").hidden = false;

  const aviso = el("aviso");
  if (dados.revisar || dados.confianca < LIMIAR_REVISAO) {
    aviso.textContent = "Não temos certeza de alguns campos. Os que pedem atenção estão destacados abaixo: confira e corrija se for preciso.";
    aviso.hidden = false;
  } else {
    aviso.textContent = "Leitura com boa confiança. Mesmo assim, confira os dados antes de confirmar.";
    aviso.hidden = false;
  }
}

function abrirManual(motivo) {
  el("resumo").hidden = true;
  const aviso = el("aviso");
  aviso.textContent = motivo || "Preencha o endereço manualmente.";
  aviso.hidden = false;
  preencherFormulario({}, []);
  mostrarEtapa("confirmacao", el("titulo-confirmacao"));
}

async function enviarFoto(evento) {
  evento.preventDefault();
  const arquivo = el("foto").files[0];
  if (!arquivo) { return; }

  const botao = el("botao-ler");
  botao.disabled = true;
  botao.textContent = "Lendo a conta...";
  mensagemErro("erro-envio", "");

  const corpo = new FormData();
  corpo.append("imagem", arquivo);

  try {
    const resposta = await fetch("extrair", { method: "POST", body: corpo });
    if (!resposta.ok) {
      abrirManual("Não foi possível ler essa foto. Tente outra mais nítida ou preencha o endereço manualmente.");
      return;
    }
    const dados = await resposta.json();
    mostrarResumo(dados);
    preencherFormulario(dados.endereco, dados.campos_revisar || []);
    mostrarEtapa("confirmacao", el("titulo-confirmacao"));
  } catch (erro) {
    abrirManual("O serviço de leitura está indisponível agora. Preencha o endereço manualmente.");
  } finally {
    botao.textContent = "Ler endereço";
    botao.disabled = !el("foto").files[0];
  }
}

function escolherArquivo() {
  const arquivo = el("foto").files[0];
  const botao = el("botao-ler");
  mensagemErro("erro-envio", "");
  if (urlPrevia) { URL.revokeObjectURL(urlPrevia); urlPrevia = null; }

  if (!arquivo) {
    el("previa").hidden = true;
    botao.disabled = true;
    return;
  }
  if (!TIPOS.includes(arquivo.type)) {
    mensagemErro("erro-envio", "Escolha uma imagem JPG, PNG ou WEBP.");
    el("foto").value = "";
    el("previa").hidden = true;
    botao.disabled = true;
    return;
  }
  if (arquivo.size > LIMITE_BYTES) {
    mensagemErro("erro-envio", "A imagem passa de 5 MB. Escolha uma foto menor.");
    el("foto").value = "";
    el("previa").hidden = true;
    botao.disabled = true;
    return;
  }

  urlPrevia = URL.createObjectURL(arquivo);
  el("previa").src = urlPrevia;
  el("previa").hidden = false;
  el("foto-nome").textContent = arquivo.name;
  botao.disabled = false;
}

function validar() {
  limparErros();
  let primeiroErro = null;
  const exigir = (nome, condicao, texto) => {
    if (condicao) { return; }
    mensagemErro(`erro-${nome}`, texto);
    campoDe(nome).classList.add("invalido");
    if (!primeiroErro) { primeiroErro = el(nome); }
  };
  exigir("cep", el("cep").value.replace(/\D/g, "").length === 8, "Informe o CEP com 8 números.");
  exigir("bairro", el("bairro").value.trim().length > 0, "Informe o bairro.");
  exigir("cidade", el("cidade").value.trim().length > 0, "Informe a cidade.");
  return primeiroErro;
}

function confirmar(evento) {
  evento.preventDefault();
  const erro = validar();
  if (erro) { erro.focus(); return; }

  const salvo = {
    bairro: el("bairro").value.trim(),
    cep: formatarCep(el("cep").value),
    cidade: el("cidade").value.trim(),
  };

  const lista = el("salvo");
  lista.replaceChildren();
  [["Bairro", salvo.bairro], ["CEP", salvo.cep], ["Cidade", salvo.cidade]].forEach(([rotulo, valor]) => {
    const dt = document.createElement("dt");
    dt.textContent = rotulo;
    const dd = document.createElement("dd");
    dd.textContent = valor;
    lista.append(dt, dd);
  });

  el("requisicao").textContent = `PUT /enderecos/meu\n${JSON.stringify(salvo, null, 2)}`;
  mostrarEtapa("final", el("titulo-final"));
}

function reiniciar() {
  el("form-envio").reset();
  el("foto-nome").textContent = "JPG, PNG ou WEBP, até 5 MB";
  escolherArquivo();
  mostrarEtapa("envio", el("foto"));
}

el("foto").addEventListener("change", escolherArquivo);
el("form-envio").addEventListener("submit", enviarFoto);
el("botao-manual").addEventListener("click", () => abrirManual("Preencha o endereço manualmente."));
el("form-endereco").addEventListener("submit", confirmar);
el("botao-voltar").addEventListener("click", reiniciar);
el("botao-novo").addEventListener("click", reiniciar);

el("cep").addEventListener("input", () => { el("cep").value = formatarCep(el("cep").value); });
el("uf").addEventListener("input", () => { el("uf").value = el("uf").value.toUpperCase().replace(/[^A-Z]/g, ""); });

CAMPOS.forEach((nome) => {
  el(nome).addEventListener("input", () => marcarRevisao(nome, false));
});
