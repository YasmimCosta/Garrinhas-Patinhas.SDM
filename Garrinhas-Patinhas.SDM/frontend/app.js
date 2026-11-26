// Frontend da clínica — comunica-se APENAS com a API privada (REST/JSON). Troque a URL se necessário.
const API = window.API_URL || "http://localhost:8080";
const GOV = window.GOV_URL || "http://localhost:8081";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
let token = sessionStorage.getItem("token"), vet = JSON.parse(sessionStorage.getItem("vet") || "null"), animalAberto = null;

function aviso(texto, tipo = "ok") {
  const m = $("#msg"); m.textContent = texto; m.className = tipo; m.hidden = false;
  clearTimeout(aviso.t); aviso.t = setTimeout(() => (m.hidden = true), 5000);
}
async function api(path, opts = {}, base = API) {
  const headers = { "Content-Type": "application/json", ...(token && base === API ? { Authorization: "Bearer " + token } : {}) };
  let r;
  try { r = await fetch(base + path, { ...opts, headers, body: opts.body ? JSON.stringify(opts.body) : undefined }); }
  catch { throw { erro: "Servidor indisponível. Verifique se a API está em execução." }; }
  const d = await r.json().catch(() => ({}));
  if (r.status === 401 && token) { sair(false); }
  if (!r.ok) throw { status: r.status, ...d };
  return d;
}
const falha = (e) => aviso((e.erro || "Erro inesperado.") + (e.campos ? " " + e.campos.join(", ") : ""), "erro");
const dados = (f) => Object.fromEntries([...new FormData(f)].filter(([, v]) => v !== ""));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const cpfFmt = (c) => (/^\d{11}$/.test(String(c || "")) ? String(c).replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4") : c || "—");
const dataBR = (d) => (d ? String(d).slice(0, 10).split("-").reverse().join("/") : "—");
const tag = (s) => `<span class="tag ${esc(s)}">${esc(s || "—")}</span>`;
const tabela = (el, cols, linhas, extra = "") =>
  (el.innerHTML = `<tr>${cols.map((c) => `<th>${c[0]}</th>`).join("")}</tr>` +
    (linhas.length ? linhas.map((l) => `<tr ${extra && extra(l)}>${cols.map((c) => `<td>${c[1](l)}</td>`).join("")}</tr>`).join("")
      : `<tr><td colspan="${cols.length}"><small>Nenhum registro.</small></td></tr>`));

// ------------------------------------------------------------------ navegação / sessão
function ir(v) {
  $$("main > section").forEach((s) => (s.hidden = s.id !== "v-" + v));
  if (v === "tutores") carregarTutores();
  if (v === "animais") carregarAnimais();
  if (v === "integracoes") carregarIntegracoes();
}
function entrou() {
  $("#nav").hidden = !token; $("#quem").textContent = vet ? `Dr(a). ${vet.nome} · CRMV ${vet.crmv}/${vet.crmv_uf}` : "";
  token ? ir("animais") : ir("login");
}
function sair(chamarApi = true) {
  if (chamarApi && token) api("/api/auth/logout", { method: "POST" }).catch(() => {});
  token = null; vet = null; sessionStorage.clear(); entrou();
}
$("#sair").onclick = () => sair();
$$("nav button[data-v]").forEach((b) => (b.onclick = () => ir(b.dataset.v)));

$("#f-login").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const d = await api("/api/auth/login", { method: "POST", body: dados(e.target) });
    token = d.token; vet = d.veterinario; sessionStorage.setItem("token", token); sessionStorage.setItem("vet", JSON.stringify(vet)); entrou();
  } catch (x) { falha(x); }
};
$("#f-cadastro").onsubmit = async (e) => {
  e.preventDefault();
  try { const d = await api("/api/auth/cadastro", { method: "POST", body: dados(e.target) });
    aviso(`Cadastro criado. Código de confirmação (e-mail simulado): ${d.codigo_confirmacao_simulado}`); }
  catch (x) { falha(x); }
};
$("#f-confirma").onsubmit = async (e) => {
  e.preventDefault();
  try { const d = await api("/api/auth/confirmar", { method: "POST", body: dados(e.target) }); aviso(d.mensagem); }
  catch (x) { falha(x); }
};

// ------------------------------------------------------------------ tutores + CEP
$("#b-cep").onclick = async () => {
  const f = $("#f-tutor");
  try {
    const d = await api("/api/cep/" + f.cep.value.replace(/\D/g, ""));
    ["logradouro", "bairro", "cidade", "uf", "codigo_ibge"].forEach((c) => (f[c].value = d[c] || ""));
    if (d.complemento) f.complemento.value = d.complemento;
    aviso("Endereço preenchido pelo ViaCEP. Você pode ajustar manualmente.");
  } catch (x) { aviso((x.erro || "Falha na consulta") + (x.preenchimento_manual ? " Preencha o endereço manualmente." : ""), "erro"); f.logradouro.focus(); }
};
let tutorEditando = null;
const CAMPOS_END = ["cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf", "codigo_ibge"];

function modoTutor(id) {                       // alterna entre "novo" e "editar"
  tutorEditando = id;
  $("#t-form-titulo").textContent = id ? `Editar tutor #${id}` : "Novo tutor";
  $("#l-situacao").hidden = !id; $("#b-cancelar").hidden = !id;
  $("#b-salvar-tutor").textContent = id ? "Salvar alterações" : "Salvar tutor";
  if (!id) $("#f-tutor").reset();
}
$("#b-cancelar").onclick = () => modoTutor(null);

$("#f-tutor").onsubmit = async (e) => {
  e.preventDefault();
  const edicao = !!tutorEditando;
  const d = edicao ? Object.fromEntries(new FormData(e.target)) : dados(e.target), end = {};
  CAMPOS_END.forEach((c) => { if (edicao || d[c]) end[c] = d[c]; delete d[c]; });
  if (!edicao) delete d.situacao;
  try {
    if (edicao) {
      await api("/api/tutores/" + tutorEditando, { method: "PUT", body: { ...d, endereco: end } });
      aviso("Perfil do tutor atualizado.");
      const id = tutorEditando; modoTutor(null); carregarTutores(); abrirTutor(id);
    } else {
      await api("/api/tutores", { method: "POST", body: { ...d, endereco: end } }); aviso("Tutor cadastrado."); e.target.reset(); carregarTutores();
    }
  } catch (x) { falha(x); }
};

async function carregarTutores() {
  try {
    const l = await api("/api/tutores");
    tabela($("#t-tutores"), [["Nome", (t) => esc(t.nome)], ["CPF", (t) => cpfFmt(t.cpf)], ["Telefone", (t) => esc(t.telefone)],
      ["E-mail", (t) => esc(t.email)], ["Situação", (t) => tag(t.situacao)]], l, (t) => `class="click" data-id="${t.id_tutor}"`);
    $$("#t-tutores tr.click").forEach((tr) => (tr.onclick = () => abrirTutor(tr.dataset.id)));
  } catch (x) { falha(x); }
}

async function abrirTutor(id) {                // perfil completo do tutor
  try {
    const t = await api("/api/tutores/" + id), e = t.endereco;
    const el = $("#detalhe-tutor"); el.hidden = false;
    el.innerHTML = `
      <h2>👤 ${esc(t.nome)} <small>#${t.id_tutor}</small> ${tag(t.situacao)}</h2>
      <div class="grid2">
        <div><h3>Dados pessoais</h3>
          <p><strong>CPF:</strong> ${cpfFmt(t.cpf)}<br><strong>Nascimento:</strong> ${dataBR(t.data_nascimento)}<br>
          <strong>Telefone:</strong> ${esc(t.telefone)}<br><strong>E-mail:</strong> ${esc(t.email)}<br>
          <strong>Cadastrado em:</strong> ${esc(t.data_cadastro)}</p></div>
        <div><h3>Endereço</h3>
          <p>${esc(e.logradouro)}, ${esc(e.numero)}${e.complemento ? " - " + esc(e.complemento) : ""}<br>
          ${esc(e.bairro)} · ${esc(e.cidade)}/${esc(e.uf)}<br><strong>CEP:</strong> ${esc(e.cep)}
          ${e.codigo_ibge ? `<br><strong>IBGE:</strong> ${esc(e.codigo_ibge)}` : ""}</p></div>
      </div>
      <h3>Animais deste tutor (${t.total_animais})</h3><div class="scroll"><table id="t-animais-tutor"></table></div>
      <div class="row" style="margin-top:.8rem"><button id="b-editar-tutor">✏️ Editar perfil</button>
        ${t.situacao === "ATIVO" ? `<button id="b-inativar-tutor" class="sec">Inativar tutor</button>` : `<button id="b-reativar-tutor" class="ok">Reativar tutor</button>`}</div>`;
    tabela($("#t-animais-tutor"), [["Animal", (a) => esc(a.nome)], ["Espécie / Raça", (a) => `${esc(a.especie)} / ${esc(a.raca)}`],
      ["Microchip", (a) => esc(a.microchip || "—")], ["Situação", (a) => tag(a.situacao)]], t.animais, (a) => `class="click" data-an="${a.id_animal}"`);
    $$("#t-animais-tutor tr.click").forEach((tr) => (tr.onclick = () => { ir("animais"); abrirAnimal(tr.dataset.an); }));
    $("#b-editar-tutor").onclick = () => {
      const f = $("#f-tutor"); modoTutor(t.id_tutor);
      ["nome", "data_nascimento", "telefone", "email", "situacao"].forEach((c) => (f[c].value = t[c] ?? ""));
      f.cpf.value = cpfFmt(t.cpf);
      CAMPOS_END.forEach((c) => (f[c].value = e[c] ?? ""));
      f.scrollIntoView({ behavior: "smooth" }); f.nome.focus();
    };
    const mudar = (situacao, msg) => async () => {
      try { await api("/api/tutores/" + id, { method: "PUT", body: { situacao } }); aviso(msg); carregarTutores(); abrirTutor(id); } catch (x) { falha(x); }
    };
    if ($("#b-inativar-tutor")) $("#b-inativar-tutor").onclick = mudar("INATIVO", "Tutor inativado.");
    if ($("#b-reativar-tutor")) $("#b-reativar-tutor").onclick = mudar("ATIVO", "Tutor reativado.");
    el.scrollIntoView({ behavior: "smooth" });
  } catch (x) { falha(x); }
}

// ------------------------------------------------------------------ animais
const opts = (l, v, t, vazio) => (vazio ? `<option value="">${vazio}</option>` : "") + l.map((i) => `<option value="${i[v]}">${esc(i[t])}</option>`).join("");
async function carregarAnimais() {
  try {
    const [tut, esp, ani] = await Promise.all([api("/api/tutores"), api("/api/especies"), api("/api/animais")]);
    const f = $("#f-animal");
    f.id_tutor.innerHTML = opts(tut.filter((t) => t.situacao === "ATIVO"), "id_tutor", "nome");
    f.id_especie.innerHTML = opts(esp, "id_especie", "nome");
    await racasDaEspecie();
    tabela($("#t-animais"), [["Nome", (a) => esc(a.nome)], ["Espécie / Raça", (a) => `${esc(a.especie)} / ${esc(a.raca)}`],
      ["Tutor", (a) => esc(a.tutor_nome)], ["Microchip", (a) => esc(a.microchip || "—")], ["Situação", (a) => tag(a.situacao)]],
      ani, (a) => `class="click" data-id="${a.id_animal}"`);
    $$("#t-animais tr.click").forEach((tr) => (tr.onclick = () => abrirAnimal(tr.dataset.id)));
  } catch (x) { falha(x); }
}
async function racasDaEspecie() {
  const f = $("#f-animal");
  const r = await api("/api/racas?id_especie=" + f.id_especie.value);
  f.id_raca.innerHTML = opts(r, "id_raca", "nome", "Sem raça definida");
}
$("#f-animal").id_especie.onchange = () => racasDaEspecie().catch(falha);
$("#f-animal").onsubmit = async (e) => {
  e.preventDefault();
  const d = dados(e.target);
  ["id_tutor", "id_especie", "id_raca", "idade_estimada_meses"].forEach((c) => { if (d[c]) d[c] = +d[c]; });
  if (d.peso_atual) d.peso_atual = +d.peso_atual;
  try { await api("/api/animais", { method: "POST", body: d }); aviso("Animal cadastrado."); e.target.reset(); carregarAnimais(); }
  catch (x) { falha(x); }
};

async function abrirAnimal(id) {
  animalAberto = id;
  try {
    const [a, mc, cons, vac] = await Promise.all([api("/api/animais/" + id), api(`/api/animais/${id}/microchips`),
      api(`/api/animais/${id}/consultas`), api(`/api/animais/${id}/vacinas`)]);
    const g = a.integracao_governo, chip = a.microchip_ativo;
    let reg = null;                                  // o que a API governamental tem registrado
    if (chip) reg = await api(`/api/animais/${id}/governo`).catch((x) => ({ falhou: x.erro || "Não foi possível consultar o governo." }));
    const el = $("#detalhe"); el.hidden = false;
    el.innerHTML = `
      <h2>🐶 ${esc(a.nome)} <small>#${a.id_animal} · ${esc(a.especie)} / ${esc(a.raca)} · tutor: ${esc(a.tutor_nome)}</small></h2>
      <p>Peso: ${esc(a.peso_atual ?? "—")} kg · Cor: ${esc(a.cor || "—")} · Nasc.: ${esc(a.data_nascimento || "~" + a.idade_estimada_meses + " meses")}</p>
      <p><strong>Microchip RFID:</strong> ${chip ? esc(chip.codigo_microchip) + ` <small>(vinculado por ${esc(chip.veterinario_nome)} em ${esc(chip.data_inicio)})</small>` : "<em>não vinculado</em>"}<br>
         <strong>Cadastro no governo:</strong> ${tag(g.cadastro_governo)} ${g.protocolo ? "protocolo " + esc(g.protocolo) : ""}
         ${g.comunicacoes_nao_confirmadas ? `· <span class="tag PENDENTE">${g.comunicacoes_nao_confirmadas} comunicação(ões) não confirmada(s)</span>` : ""}</p>
      <h3>Registro na API governamental</h3><div id="gov-registro"></div>
      <div class="grid2">
        <div><h3>Vincular / substituir microchip</h3>
          <form id="f-chip"><div class="row"><label>Código (15 dígitos)<input name="codigo_microchip" pattern="\\d{15}" required></label>
          <label>Motivo (se substituição)<input name="motivo"></label></div><button>Vincular</button></form>
          <h3>Histórico de microchips</h3><div class="scroll"><table id="t-chips"></table></div></div>
        <div><h3>Nova consulta</h3>
          <form id="f-cons"><div class="row"><label>Data/hora<input name="data_hora" type="datetime-local" required></label>
          <label>Situação<select name="status"><option value="REALIZADA">Realizada</option><option value="AGENDADA">Agendada</option><option value="CANCELADA">Cancelada</option><option value="NAO_COMPARECEU">Não compareceu</option></select></label></div>
          <label>Motivo<input name="motivo" required></label><label>Anamnese<textarea name="anamnese" rows="2"></textarea></label>
          <div class="row"><label>Sintomas<input name="sintomas"></label><label>Diagnóstico<input name="diagnostico"></label></div>
          <div class="row"><label>Tratamento<input name="tratamento"></label><label>Prescrição<input name="prescricao"></label></div>
          <div class="row"><label>Peso (kg)<input name="peso" type="number" step="0.01"></label><label>Temp. (°C)<input name="temperatura" type="number" step="0.1"></label></div>
          <button>Registrar consulta</button></form></div>
      </div>
      <h3>Histórico clínico</h3><div class="scroll"><table id="t-cons"></table></div>
      <h3>Registrar vacina</h3>
      <form id="f-vac"><div class="row"><label>Nome<input name="nome" required></label>
        <label>Tipo<select name="tipo"><option value="ANTIRRABICA">Antirrábica</option><option value="POLIVALENTE">Polivalente</option><option value="GRIPE">Gripe</option><option value="GIARDIA">Giárdia</option><option value="OUTRA">Outra</option></select></label>
        <label>Fabricante<input name="fabricante" required></label><label>Lote<input name="lote" required></label></div>
        <div class="row"><label>Aplicação<input name="data_aplicacao" type="date" required></label><label>Validade do lote<input name="validade_lote" type="date"></label>
        <label>Dose/etapa<input name="dose"></label><label>Via<input name="via_aplicacao"></label><label>Próxima dose<input name="proxima_dose" type="date"></label></div>
        <button>Registrar vacina</button></form>
      <h3>Próximas doses</h3><div id="proximas"></div>
      <h3>Histórico de vacinação</h3><div class="scroll"><table id="t-vac"></table></div>`;
    $("#gov-registro").innerHTML = !chip ? "<small>Vincule um microchip para registrar o animal no governo.</small>"
      : reg.falhou ? `<small>⚠️ ${esc(reg.falhou)} (microchip ${esc(chip.codigo_microchip)})</small>`
      : `<p><strong>Microchip:</strong> ${esc(reg.microchip)} · <strong>CPF do tutor:</strong> ${cpfFmt(reg.tutor_cpf)} · <strong>Tutor:</strong> ${esc(reg.tutor_nome)}<br>
         <small>Responsável: ${esc(reg.responsavel_crmv || "—")} · registrado em ${esc(reg.criado_em)} · atualizado em ${esc(reg.atualizado_em)}</small></p>
         <div class="scroll"><table id="t-gov-vac"></table></div>`;
    if (reg && !reg.falhou) tabela($("#t-gov-vac"), [["Vacinação antirrábica", (v) => esc(v.vacina_nome)], ["Data", (v) => esc(v.data_aplicacao)],
      ["Lote", (v) => esc(v.lote)], ["Microchip", (v) => esc(v.microchip)], ["CPF do tutor", (v) => cpfFmt(v.tutor_cpf || reg.tutor_cpf)],
      ["Protocolo", (v) => esc(v.protocolo)]], reg.vacinacoes_antirrabicas);
    tabela($("#t-chips"), [["Código", (c) => esc(c.codigo_microchip)], ["Início", (c) => esc(c.data_inicio)], ["Fim", (c) => esc(c.data_fim || "ativo")],
      ["Veterinário", (c) => esc(c.veterinario_nome)], ["Motivo", (c) => esc(c.motivo_fim || "")]], mc);
    tabela($("#t-cons"), [["Data", (c) => esc(c.data_hora.replace("T", " "))], ["Motivo", (c) => esc(c.motivo)], ["Diagnóstico", (c) => esc(c.diagnostico || "")],
      ["Veterinário", (c) => esc(c.veterinario_nome)], ["Situação", (c) => tag(c.status)]], cons);
    $("#proximas").innerHTML = vac.proximas_doses.length ? vac.proximas_doses.map((p) => `<span class="tag ${p.atrasada ? "FALHA" : "ENVIADA"}">${esc(p.nome)}: ${esc(p.proxima_dose)}${p.atrasada ? " (atrasada)" : ""}</span> `).join("") : "<small>Nenhuma dose prevista.</small>";
    tabela($("#t-vac"), [["Aplicação", (v) => esc(v.data_aplicacao)], ["Vacina", (v) => esc(v.nome) + (v.antirrabica ? " 🦠 <small>antirrábica</small>" : "")],
      ["Lote", (v) => esc(v.lote)], ["Situação local", (v) => tag(v.status)],
      ["Comunicação ao governo", (v) => v.antirrabica ? tag(v.comunicacao_status) + (v.comunicacao_protocolo ? ` <small>${esc(v.comunicacao_protocolo)}</small>` : "") : "<small>não obrigatória</small>"]], vac.historico);
    $("#f-chip").onsubmit = async (e) => { e.preventDefault();
      try { const r = await api(`/api/animais/${id}/microchip`, { method: "POST", body: dados(e.target) }); aviso("Microchip vinculado. Governo: " + r.integracao_governo.cadastro_governo); abrirAnimal(id); carregarAnimais(); } catch (x) { falha(x); } };
    $("#f-cons").onsubmit = async (e) => { e.preventDefault(); const d = dados(e.target); d.id_animal = +id;
      try { await api("/api/consultas", { method: "POST", body: d }); aviso("Consulta registrada."); abrirAnimal(id); } catch (x) { falha(x); } };
    $("#f-vac").onsubmit = async (e) => { e.preventDefault(); const d = dados(e.target); d.id_animal = +id;
      try { const r = await api("/api/vacinas", { method: "POST", body: d }); const c = r.comunicacao_governo;
        aviso(c ? `Vacina registrada localmente. Comunicação ao governo: ${c.status}${c.status === "PENDENTE" ? " (será reenviada)" : ""}` : "Vacina registrada (sem comunicação obrigatória).", c && c.status !== "CONFIRMADA" ? "erro" : "ok");
        abrirAnimal(id); } catch (x) { falha(x); } };
    el.scrollIntoView({ behavior: "smooth" });
  } catch (x) { falha(x); }
}

// ------------------------------------------------------------------ integrações
async function modoGov() {
  try { const m = await api("/api/governo/admin/indisponibilidade", {}, GOV); $("#gov-modo").textContent = { off: "Disponível", 503: "Indisponível (503)", timeout: "Lento (timeout)" }[m.modo]; }
  catch { $("#gov-modo").textContent = "Fora do ar (API governamental não responde)"; }
}
async function carregarIntegracoes() {
  modoGov();
  try {
    const l = await api("/api/integracoes" + ($("#f-status").value ? "?status=" + $("#f-status").value : ""));
    tabela($("#t-integ"), [["#", (i) => i.id_integracao], ["Operação", (i) => esc(i.tipo_operacao)], ["Animal", (i) => esc(i.animal_nome)],
      ["Microchip", (i) => esc(i.microchip || "—")], ["Tutor / CPF", (i) => `${esc(i.tutor_nome)}<br><small>${cpfFmt(i.tutor_cpf)}</small>`],
      ["Situação", (i) => tag(i.status)], ["Protocolo", (i) => esc(i.protocolo_externo || "—")], ["Tentativas", (i) => i.tentativas],
      ["Erro", (i) => `<small>${esc(i.mensagem_erro || "")}</small>`],
      ["", (i) => i.status !== "CONFIRMADA" ? `<button class="mini" data-re="${i.id_integracao}">Reenviar</button>` : ""]], l);
    $$("[data-re]").forEach((b) => (b.onclick = async () => { try { const r = await api(`/api/integracoes/${b.dataset.re}/reenviar`, { method: "POST" }); aviso("Resultado: " + r.status, r.status === "CONFIRMADA" ? "ok" : "erro"); carregarIntegracoes(); } catch (x) { falha(x); } }));
  } catch (x) { falha(x); }
}
$("#f-status").onchange = carregarIntegracoes;
$$("[data-gov]").forEach((b) => (b.onclick = async () => { try { await api("/api/governo/admin/indisponibilidade", { method: "POST", body: { modo: b.dataset.gov } }, GOV); modoGov(); aviso("Simulação alterada."); } catch (x) { falha(x); } }));
$("#b-reproc").onclick = async () => { try { const r = await api("/api/integracoes/reprocessar-pendentes", { method: "POST" }); aviso(`${r.reprocessadas.length} operação(ões) reprocessada(s).`); carregarIntegracoes(); } catch (x) { falha(x); } };

entrou();
