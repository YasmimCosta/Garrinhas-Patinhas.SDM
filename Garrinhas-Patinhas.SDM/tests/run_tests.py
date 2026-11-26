"""
Testes de ponta a ponta dos 16 cenários obrigatórios (seção 9 do enunciado) + extras.
Sobe os 3 serviços em portas de teste com bancos temporários, executa e gera
docs/testes/relatorio-testes.md.   Uso:  python tests/run_tests.py
"""
import datetime as dt
import os
import subprocess
import sys
import tempfile
import time

import requests

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PY = sys.executable
CL, GV, MK = "http://localhost:18080", "http://localhost:18081", "http://localhost:18099"
KEY = {"X-API-Key": "chave-demo-governo"}
resultados, procs = [], []


def cpf(base9):
    d = [int(c) for c in base9]
    for n in (9, 10):
        r = (sum(d[i] * (n + 1 - i) for i in range(n)) * 10) % 11
        d.append(0 if r == 10 else r)
    return "".join(map(str, d))


def check(num, nome, cond, evidencia=""):
    resultados.append((num, nome, bool(cond), evidencia))
    print(("  OK   " if cond else "  FALHA"), num, nome, "|", evidencia)


def subir(cmd, cwd, env):
    p = subprocess.Popen(cmd, cwd=cwd, env={**os.environ, **env}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    procs.append(p)


def esperar(url):
    for _ in range(60):
        try:
            requests.get(url, timeout=1)
            return
        except requests.RequestException:
            time.sleep(0.25)
    raise RuntimeError(f"Serviço não subiu: {url}")


def gov_modo(m):
    return requests.post(f"{GV}/api/governo/admin/indisponibilidade", json={"modo": m}).json()


def main():
    tmp = tempfile.mkdtemp()
    amb = {"CLINICA_DB": f"{tmp}/clinica.db", "GOVERNO_DB": f"{tmp}/governo.db", "CLINICA_PORT": "18080",
           "GOVERNO_PORT": "18081", "MOCK_VIACEP_PORT": "18099", "VIACEP_URL": f"{MK}/ws", "VIACEP_TIMEOUT_S": "1",
           "GOVERNO_API_URL": GV, "INTEGRACAO_TIMEOUT_S": "1", "GOVERNO_TIMEOUT_SIMULADO_S": "3",
           "REENVIO_AUTOMATICO_S": "3", "INTEGRACAO_MAX_TENTATIVAS": "6"}
    subir([PY, "mock_viacep.py"], os.path.join(RAIZ, "tests"), amb)
    subir([PY, "app.py"], os.path.join(RAIZ, "api-governo-simulada"), amb)
    subir([PY, "app.py"], os.path.join(RAIZ, "backend-clinica"), amb)
    esperar(f"{MK}/ws/20040020/json/"); esperar(f"{GV}/api/governo/health"); esperar(f"{CL}/api/health")

    L = lambda email, senha="Senha@123": requests.post(f"{CL}/api/auth/login", json={"email": email, "senha": senha})
    # ---------------------------------------------------------------- AUTENTICAÇÃO
    r = L("ana.souza@clinica.test")
    token = r.json().get("token")
    H = {"Authorization": f"Bearer {token}"}
    check(1, "Login de veterinário ativo e com senha confirmada", r.status_code == 200 and token, f"HTTP {r.status_code}, JWT emitido")
    r = L("bruno.lima@clinica.test")
    check(2, "Bloqueio de veterinário inativo", r.status_code == 403, f"HTTP {r.status_code}: {r.json().get('erro')}")
    r = L("carla.dias@clinica.test")
    check(3, "Bloqueio de veterinário com senha não confirmada", r.status_code == 403, f"HTTP {r.status_code}: {r.json().get('erro')}")
    r = L("ana.souza@clinica.test", "errada123")
    check(4, "Rejeição de senha incorreta", r.status_code == 401, f"HTTP {r.status_code}: {r.json().get('erro')}")

    # ---------------------------------------------------------------- TUTOR / CEP
    cpf_t = cpf("390533447")
    tutor = {"nome": "João Teste Fictício", "cpf": cpf_t, "data_nascimento": "1985-02-15", "email": "joao@exemplo.test",
             "telefone": "21977770000",
             "endereco": {"cep": "20040020", "logradouro": "Rua da Assembleia", "numero": "100", "bairro": "Centro",
                          "cidade": "Rio de Janeiro", "uf": "RJ", "codigo_ibge": "3304557"}}
    r1 = requests.post(f"{CL}/api/tutores", json=tutor, headers=H)
    r2 = requests.post(f"{CL}/api/tutores", json=tutor, headers=H)
    r3 = requests.post(f"{CL}/api/tutores", json={**tutor, "cpf": "11111111111"}, headers=H)
    id_tutor = r1.json().get("id_tutor")
    check(5, "Cadastro de tutor e validação de CPF duplicado", r1.status_code == 201 and r2.status_code == 409,
          f"cadastro HTTP {r1.status_code}; CPF repetido HTTP {r2.status_code}; CPF inválido HTTP {r3.status_code}")
    rc = requests.get(f"{CL}/api/cep/20040-020", headers=H)
    rn = requests.get(f"{CL}/api/cep/99999999", headers=H)
    rf = requests.get(f"{CL}/api/cep/123", headers=H)
    rt = requests.get(f"{CL}/api/cep/11111111", headers=H)
    check(6, "Consulta de CEP válido e tratamento de CEP inexistente",
          rc.status_code == 200 and rc.json()["cidade"] == "Rio de Janeiro" and rn.status_code == 404 and rn.json().get("preenchimento_manual"),
          f"válido HTTP {rc.status_code}; inexistente HTTP {rn.status_code}; formato inválido HTTP {rf.status_code}; timeout HTTP {rt.status_code}")
    check("6b", "CEP: timeout do serviço externo tratado (504)", rt.status_code == 504, f"HTTP {rt.status_code}")

    # ---------------------------------------------------------------- ANIMAL / MICROCHIP
    animal = {"nome": "Mel", "id_tutor": id_tutor, "id_especie": 2, "id_raca": 4, "sexo": "F", "cor": "Creme",
              "data_nascimento": "2022-06-01", "peso_atual": 4.2}
    ra = requests.post(f"{CL}/api/animais", json=animal, headers=H)
    id_a = ra.json().get("id_animal")
    rinc = requests.post(f"{CL}/api/animais", json={**animal, "id_especie": 1}, headers=H)   # raça de gato em espécie cão
    rsem = requests.post(f"{CL}/api/animais", json={**animal, "nome": "Sem Raça", "id_raca": None}, headers=H)
    CHIP1 = "076000000000001"
    rm = requests.post(f"{CL}/api/animais/{id_a}/microchip", json={"codigo_microchip": CHIP1}, headers=H)
    check(7, "Cadastro de animal e vínculo de microchip",
          ra.status_code == 201 and rm.status_code == 201 and rm.json()["vinculo"]["id_veterinario"] == 1,
          f"animal HTTP {ra.status_code}; microchip HTTP {rm.status_code}, vínculo pelo veterinário id=1; "
          f"raça incompatível HTTP {rinc.status_code}; sem raça HTTP {rsem.status_code}")
    outro = requests.post(f"{CL}/api/animais", json={**animal, "nome": "Outro"}, headers=H).json()["id_animal"]
    rdup = requests.post(f"{CL}/api/animais/{outro}/microchip", json={"codigo_microchip": CHIP1}, headers=H)
    check(8, "Rejeição de microchip já utilizado", rdup.status_code == 409, f"HTTP {rdup.status_code}: {rdup.json().get('erro')}")

    # ---------------------------------------------------------------- CONSULTA / VACINA
    rcons = requests.post(f"{CL}/api/consultas", headers=H, json={"id_animal": id_a, "data_hora": "2026-11-20T10:00",
          "motivo": "Check-up anual", "anamnese": "Sem queixas", "diagnostico": "Saudável", "peso": 4.3, "temperatura": 38.5})
    hist = requests.get(f"{CL}/api/animais/{id_a}/consultas", headers=H).json()
    check(9, "Registro de consulta e consulta ao histórico clínico",
          rcons.status_code == 201 and len(hist) == 1 and hist[0]["motivo"] == "Check-up anual",
          f"consulta HTTP {rcons.status_code}; histórico com {len(hist)} item(ns)")
    futuro = (dt.date.today() + dt.timedelta(days=30)).isoformat()
    hoje, val = dt.date.today().isoformat(), (dt.date.today() + dt.timedelta(days=365)).isoformat()
    vac = lambda **k: requests.post(f"{CL}/api/vacinas", headers=H, json={"id_animal": id_a, "fabricante": "LabFicticio",
          "data_aplicacao": hoje, "validade_lote": val, "dose": "Dose 1", "via_aplicacao": "Subcutânea", **k})
    rv = vac(nome="V10", tipo="POLIVALENTE", lote="LOTE-POLI-1", proxima_dose=futuro)
    pv = requests.get(f"{CL}/api/animais/{id_a}/vacinas", headers=H).json()
    check(10, "Registro de vacina e consulta às próximas doses",
          rv.status_code == 201 and any(p["proxima_dose"] == futuro for p in pv["proximas_doses"]),
          f"vacina HTTP {rv.status_code}; próximas doses: {[p['proxima_dose'] for p in pv['proximas_doses']]}")

    # ---------------------------------------------------------------- GOVERNO
    gcad = requests.get(f"{GV}/api/governo/animais/{CHIP1}", headers=KEY)
    ints = requests.get(f"{CL}/api/integracoes?id_animal={id_a}", headers=H).json()
    requests.put(f"{CL}/api/animais/{id_a}", json={"cor": "Chocolate"}, headers=H)
    gatu = requests.get(f"{GV}/api/governo/animais/{CHIP1}", headers=KEY).json()
    tipos = {i["tipo_operacao"]: i["status"] for i in ints}
    check(11, "Cadastro e atualização de animal na API governamental simulada",
          gcad.status_code == 200 and tipos.get("CADASTRO_ANIMAL") == "CONFIRMADA" and gatu["cor"] == "Chocolate",
          f"governo HTTP {gcad.status_code}; cadastro {tipos.get('CADASTRO_ANIMAL')}; cor no governo após PUT = {gatu['cor']}")
    check(13, "Ausência de comunicação obrigatória para vacina não antirrábica",
          rv.json()["comunicacao_governo"] is None and len(gatu["vacinacoes_antirrabicas"]) == 0,
          "vacina polivalente: sem integração criada e 0 vacinações no governo")

    rr = vac(nome="Raiva Premium", tipo="ANTIRRABICA", lote="LOTE-RAIVA-1", proxima_dose=futuro)
    cg = rr.json()["comunicacao_governo"]
    ggov = requests.get(f"{GV}/api/governo/animais/{CHIP1}", headers=KEY).json()
    gop = requests.get(f"{GV}/api/governo/operacoes/{cg['protocolo_externo']}", headers=KEY).json()
    check(12, "Envio obrigatório de vacina antirrábica",
          rr.status_code == 201 and cg["status"] == "CONFIRMADA" and cg["protocolo_externo"] and gop["status"] == "PROCESSADO"
          and len(ggov["vacinacoes_antirrabicas"]) == 1,
          f"integração {cg['status']}, protocolo {cg['protocolo_externo']}, 1 vacinação registrada no governo")
    id_vac1 = rr.json()["vacina"]["id_vacina"]

    # 16 — repetição sem duplicidade
    payload = {"microchip": CHIP1, "id_animal_origem": id_a, "nome_animal": "Mel", "data_aplicacao": hoje,
               "vacina_nome": "Raiva Premium", "fabricante": "LabFicticio", "lote": "LOTE-RAIVA-1",
               "veterinario_nome": "Dra. Ana Souza", "veterinario_crmv": "12345/RJ"}
    rep1 = requests.post(f"{GV}/api/governo/vacinacoes-antirrabicas", json=payload,
                         headers={**KEY, "Idempotency-Key": f"VACINA_ANTIRRABICA-{id_vac1}"})
    rep2 = requests.post(f"{GV}/api/governo/vacinacoes-antirrabicas", json=payload, headers={**KEY, "Idempotency-Key": "outra-chave"})
    rep3 = requests.post(f"{CL}/api/integracoes/{cg['id_integracao']}/reenviar", headers=H)
    n = len(requests.get(f"{GV}/api/governo/animais/{CHIP1}", headers=KEY).json()["vacinacoes_antirrabicas"])
    check(16, "Repetição de solicitação sem duplicidade de vacinação no serviço externo",
          rep1.json().get("duplicado") and rep2.json().get("duplicado") and rep1.json()["protocolo"] == cg["protocolo_externo"] and n == 1,
          f"mesma chave -> duplicado={rep1.json().get('duplicado')}, protocolo igual; chave diferente -> duplicado={rep2.json().get('duplicado')}; "
          f"reenvio pela clínica HTTP {rep3.status_code}; vacinações no governo = {n}")

    # 14 e 15 — indisponibilidade e regularização
    gov_modo("503")
    rp = vac(nome="Raiva Premium", tipo="ANTIRRABICA", lote="LOTE-RAIVA-2")
    cp = rp.json()["comunicacao_governo"]
    local = [v for v in requests.get(f"{CL}/api/animais/{id_a}/vacinas", headers=H).json()["historico"] if v["lote"] == "LOTE-RAIVA-2"]
    check(14, "Indisponibilidade da API governamental e registro de pendência",
          rp.status_code == 201 and cp["status"] == "PENDENTE" and cp["tentativas"] >= 1 and len(local) == 1
          and local[0]["comunicacao_status"] == "PENDENTE",
          f"vacina gravada localmente (HTTP {rp.status_code}); integração {cp['status']}, tentativas={cp['tentativas']}, erro='{cp['mensagem_erro']}'")
    rg503 = requests.get(f"{CL}/api/animais/{id_a}/governo", headers=H)
    check("E9b", "Consulta ao registro governamental com o governo fora do ar -> 503 tratado", rg503.status_code == 503,
          f"HTTP {rg503.status_code}: {rg503.json().get('erro')}")
    gov_modo("off")
    rre = requests.post(f"{CL}/api/integracoes/{cp['id_integracao']}/reenviar", headers=H).json()
    n = len(requests.get(f"{GV}/api/governo/animais/{CHIP1}", headers=KEY).json()["vacinacoes_antirrabicas"])
    check(15, "Reenvio de comunicação pendente e confirmação posterior",
          rre["status"] == "CONFIRMADA" and rre["protocolo_externo"] and n == 2,
          f"após reenvio: {rre['status']}, protocolo {rre['protocolo_externo']}, tentativas={rre['tentativas']}; governo com {n} vacinações (sem duplicar)")

    # ---------------------------------------------------------------- EXTRAS
    # --- CPF do tutor e microchip nas partes governamentais
    ints = requests.get(f"{CL}/api/integracoes?id_animal={id_a}", headers=H).json()
    check("E11", "Integrações exibem microchip e CPF do tutor",
          len(ints) >= 3 and all(i["microchip"] == CHIP1 and i["tutor_cpf"] == cpf_t for i in ints),
          f"{len(ints)} operações, todas com microchip {CHIP1} e CPF {cpf_t}")
    gop2 = requests.get(f"{GV}/api/governo/operacoes/{cg['protocolo_externo']}", headers=KEY).json()
    glist = requests.get(f"{GV}/api/governo/animais", headers=KEY).json()
    linha = next((x for x in glist if x["microchip"] == CHIP1), {})
    check("E12", "API governamental exibe CPF do tutor e microchip (operação e listagem)",
          gop2.get("tutor_cpf") == cpf_t and gop2.get("microchip") == CHIP1 and linha.get("tutor_cpf") == cpf_t,
          f"operação: microchip={gop2.get('microchip')}, tutor_cpf={gop2.get('tutor_cpf')}; listagem: {linha.get('microchip')} / {linha.get('tutor_cpf')}")
    rg = requests.get(f"{CL}/api/animais/{id_a}/governo", headers=H).json()
    vacs = rg.get("vacinacoes_antirrabicas", [])
    check("E13", "Registro governamental do animal traz microchip, CPF do tutor e vacinações com CPF",
          rg.get("microchip") == CHIP1 and rg.get("tutor_cpf") == cpf_t and len(vacs) == 2 and all(v["tutor_cpf"] == cpf_t for v in vacs),
          f"microchip={rg.get('microchip')}, tutor_cpf={rg.get('tutor_cpf')}, {len(vacs)} vacinações antirrábicas com CPF")

    # --- perfil do tutor: ver tudo e editar
    perfil = requests.get(f"{CL}/api/tutores/{id_tutor}", headers=H).json()
    check("E9", "Perfil do tutor traz dados pessoais, endereço completo e animais",
          perfil["cpf"] == cpf_t and perfil["endereco"]["logradouro"] and perfil["data_cadastro"] and perfil["situacao"] == "ATIVO"
          and perfil["total_animais"] == len(perfil["animais"]) >= 2 and any(a["microchip"] == CHIP1 for a in perfil["animais"]),
          f"{perfil['total_animais']} animais; endereço {perfil['endereco']['logradouro']}, {perfil['endereco']['cidade']}/{perfil['endereco']['uf']}")
    novo_cpf = cpf("135792468")
    ed = requests.put(f"{CL}/api/tutores/{id_tutor}", headers=H, json={"nome": "João Teste Editado", "telefone": "21966660000",
          "cpf": novo_cpf, "endereco": {"numero": "200", "complemento": "Apto 5", "cidade": "Niterói"}})
    reler = requests.get(f"{CL}/api/tutores/{id_tutor}", headers=H).json()
    dup = requests.put(f"{CL}/api/tutores/{id_tutor}", headers=H, json={"cpf": "98765432100"})
    inv = requests.put(f"{CL}/api/tutores/{id_tutor}", headers=H, json={"cpf": "11111111111"})
    gnov = requests.get(f"{GV}/api/governo/animais/{CHIP1}", headers=KEY).json()
    check("E10", "Edição do perfil do tutor (dados + endereço), validação de CPF e propagação ao governo",
          ed.status_code == 200 and reler["nome"] == "João Teste Editado" and reler["cpf"] == novo_cpf
          and reler["endereco"]["numero"] == "200" and reler["endereco"]["cidade"] == "Niterói"
          and dup.status_code == 409 and inv.status_code == 422
          and gnov["tutor_cpf"] == novo_cpf and gnov["tutor_nome"] == "João Teste Editado",
          f"edição HTTP {ed.status_code}; CPF duplicado HTTP {dup.status_code}; CPF inválido HTTP {inv.status_code}; "
          f"governo atualizado: tutor_cpf={gnov['tutor_cpf']}, tutor_nome={gnov['tutor_nome']}")
    gov_modo("timeout")
    rto = vac(nome="Raiva Premium", tipo="ANTIRRABICA", lote="LOTE-RAIVA-3").json()["comunicacao_governo"]
    check("E1", "Timeout na comunicação mantém pendência", rto["status"] == "PENDENTE" and "Timeout" in (rto["mensagem_erro"] or ""),
          f"status {rto['status']}: {rto['mensagem_erro']}")
    gov_modo("off")
    time.sleep(1)
    gov_modo("503")
    rau = vac(nome="Raiva Premium", tipo="ANTIRRABICA", lote="LOTE-RAIVA-4").json()["comunicacao_governo"]
    gov_modo("off")
    st = rau["status"]
    for _ in range(25):                           # reenvio AUTOMÁTICO (thread a cada 3 s)
        time.sleep(1)
        st = requests.get(f"{CL}/api/integracoes/{rau['id_integracao']}", headers=H).json()["status"]
        if st == "CONFIRMADA":
            break
    check("E2", "Reenvio automático regulariza pendências sem intervenção", st == "CONFIRMADA", f"status final {st}")
    sem_chip = requests.post(f"{CL}/api/animais", json={**animal, "nome": "SemChip"}, headers=H).json()["id_animal"]
    rsc = requests.post(f"{CL}/api/vacinas", headers=H, json={"id_animal": sem_chip, "nome": "Raiva", "tipo": "ANTIRRABICA",
          "fabricante": "X", "lote": "L", "data_aplicacao": hoje})
    check("E3", "Antirrábica exige animal com microchip", rsc.status_code == 422, f"HTTP {rsc.status_code}")
    CHIP2 = "076000000000002"
    rsub = requests.post(f"{CL}/api/animais/{id_a}/microchip", json={"codigo_microchip": CHIP2, "motivo": "Chip danificado"}, headers=H)
    hm = requests.get(f"{CL}/api/animais/{id_a}/microchips", headers=H).json()
    check("E4", "Substituição de microchip preserva o histórico",
          rsub.status_code == 201 and len(hm) == 2 and hm[1]["data_fim"] and hm[0]["data_fim"] is None,
          f"{len(hm)} vínculos; anterior encerrado com motivo '{hm[1]['motivo_fim']}'")
    check("E5", "Endpoints privados exigem autenticação", requests.get(f"{CL}/api/animais").status_code == 401, "GET /api/animais sem token -> 401")
    requests.post(f"{CL}/api/auth/logout", headers=H)
    check("E6", "Logout encerra a sessão (token revogado)", requests.get(f"{CL}/api/animais", headers=H).status_code == 401, "token após logout -> 401")
    nv = requests.post(f"{CL}/api/auth/cadastro", json={"nome": "Dr. Novo", "cpf": cpf("246813579"), "crmv": "777", "crmv_uf": "RJ",
          "email": "novo@clinica.test", "senha": "Outra@1234"}).json()
    antes = L("novo@clinica.test", "Outra@1234").status_code
    requests.post(f"{CL}/api/auth/confirmar", json={"email": "novo@clinica.test", "codigo": nv["codigo_confirmacao_simulado"]})
    depois = L("novo@clinica.test", "Outra@1234").status_code
    check("E7", "Fluxo de confirmação de senha (cadastro -> código -> login)", antes == 403 and depois == 200, f"antes {antes}, depois {depois}")
    rv_gov = requests.post(f"{GV}/api/governo/animais", json={"microchip": "123"}, headers=KEY)
    rk = requests.post(f"{GV}/api/governo/animais", json={})
    check("E8", "Governo valida dados (422) e exige credencial (401)", rv_gov.status_code == 422 and rk.status_code == 401,
          f"inválido HTTP {rv_gov.status_code}; sem chave HTTP {rk.status_code}")


def relatorio():
    ok = sum(1 for r in resultados if r[2])
    linhas = ["# Relatório de testes executados", "",
              f"Execução: {dt.datetime.now():%d/%m/%Y %H:%M} · Comando: `python tests/run_tests.py`", "",
              f"**Resultado: {ok}/{len(resultados)} verificações aprovadas.**", "",
              "Ambiente: Python 3, Flask, SQLite; três serviços reais em portas de teste (clínica 18080, governo 18081) "
              "com bancos temporários. O ViaCEP foi substituído por um *mock* local porque o ambiente de execução não tinha acesso "
              "à internet; **repita o cenário 6 com o ViaCEP real** (`VIACEP_URL=https://viacep.com.br/ws`) antes da apresentação.", "",
              "| # | Cenário | Resultado | Evidência |", "|---|---|---|---|"]
    def chave(r):
        n = str(r[0]); return (0, int(n), "") if n.isdigit() else ((0, int(n[:-1]), n[-1]) if n[:-1].isdigit() else (1, 0, n))
    for num, nome, cond, ev in sorted(resultados, key=chave):
        linhas.append(f"| {num} | {nome} | {'✅ Aprovado' if cond else '❌ Falhou'} | {ev.replace('|', '/')} |")
    linhas += ["", "Os cenários numerados de 1 a 16 correspondem à seção 9 do enunciado; os demais (`6b`, `E1`…`E8`) são testes adicionais."]
    caminho = os.path.join(RAIZ, "docs", "testes", "relatorio-testes.md")
    open(caminho, "w", encoding="utf-8").write("\n".join(linhas) + "\n")
    print(f"\n{ok}/{len(resultados)} aprovados -> {caminho}")
    return ok == len(resultados)


if __name__ == "__main__":
    try:
        main()
        sucesso = relatorio()
    finally:
        for p in procs:
            p.terminate()
    sys.exit(0 if sucesso else 1)
