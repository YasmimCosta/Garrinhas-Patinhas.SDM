"""
API GOVERNAMENTAL SIMULADA — registro de animais com microchip RFID.
*** Serviço FICTÍCIO, para fins acadêmicos. Não é integração oficial com órgãos reais. ***
Execute: python app.py   (porta 8081)
"""
import json
import os
import re
import sqlite3
import time
import uuid
import datetime as dt

from dotenv import load_dotenv
from flask import Flask, request, jsonify

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, "..", ".env"))
DB_PATH = os.getenv("GOVERNO_DB", os.path.join(BASE, "governo.db"))
SQL_PATH = os.path.join(BASE, "..", "database", "governo", "01_schema.sql")
API_KEY = os.getenv("GOVERNO_API_KEY", "chave-demo-governo")
PORT = int(os.getenv("GOVERNO_PORT", "8081"))
TIMEOUT_SIMULADO_S = float(os.getenv("GOVERNO_TIMEOUT_SIMULADO_S", "6"))

app = Flask(__name__)


def conn():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    if not os.path.exists(DB_PATH):
        c = conn()
        c.executescript(open(SQL_PATH, encoding="utf-8").read())
        c.commit()
        c.close()


def migrar():
    """Bancos criados antes desta versão: adiciona as colunas de tutor na vacinação."""
    c = conn()
    cols = [r["name"] for r in c.execute("PRAGMA table_info(vacinacao_antirrabica)")]
    for nome in ("tutor_nome", "tutor_cpf"):
        if nome not in cols:
            c.execute(f"ALTER TABLE vacinacao_antirrabica ADD COLUMN {nome} TEXT")
    c.commit()
    c.close()


init_db()
migrar()


def agora():
    return dt.datetime.now().isoformat(timespec="seconds")


def novo_protocolo():
    return f"GOV-{dt.date.today():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


def cpf_valido(cpf):
    c = re.sub(r"\D", "", str(cpf or ""))
    if len(c) != 11 or c == c[0] * 11:
        return False
    for n in (9, 10):
        dv = (sum(int(c[i]) * (n + 1 - i) for i in range(n)) * 10) % 11
        if (0 if dv == 10 else dv) != int(c[n]):
            return False
    return True


def modo_indisponibilidade():
    c = conn()
    v = c.execute("SELECT valor FROM configuracao WHERE chave='indisponibilidade'").fetchone()["valor"]
    c.close()
    return v


@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type, Idempotency-Key, X-API-Key"
    r.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
    return r


@app.before_request
def portao():
    if request.method == "OPTIONS" or not request.path.startswith("/api/governo"):
        return None
    if request.path.startswith("/api/governo/admin") or request.path == "/api/governo/health":
        return None
    modo = modo_indisponibilidade()
    if modo == "503":
        return jsonify({"erro": "Serviço governamental temporariamente indisponível (simulado)."}), 503
    if modo == "timeout":
        time.sleep(TIMEOUT_SIMULADO_S)                 # força timeout no cliente
        return jsonify({"erro": "Gateway timeout (simulado)."}), 504
    if request.headers.get("X-API-Key") != API_KEY:
        return jsonify({"erro": "Credencial inválida."}), 401
    return None


def invalido(detalhes):
    return jsonify({"erro": "Dados inválidos.", "detalhes": detalhes}), 422


def replay(c):
    """Mesma Idempotency-Key => devolve a resposta original, sem reprocessar."""
    chave = request.headers.get("Idempotency-Key")
    if chave:
        op = c.execute("SELECT resposta_json FROM operacao WHERE chave_idempotencia=?", (chave,)).fetchone()
        if op:
            resp = json.loads(op["resposta_json"])
            resp["duplicado"] = True
            return jsonify(resp), 200
    return None


def registrar_op(c, tipo, microchip, resposta):
    protocolo = novo_protocolo()
    resposta = {**resposta, "protocolo": protocolo, "status": "PROCESSADO", "duplicado": False}
    c.execute("INSERT INTO operacao VALUES (?,?,?,?,?,?,?)",
              (protocolo, tipo, microchip, "PROCESSADO", request.headers.get("Idempotency-Key"),
               json.dumps(resposta, ensure_ascii=False), agora()))
    return resposta


# ------------------------------------------------------------------ administração da simulação
@app.get("/api/governo/health")
def health():
    return jsonify({"status": "ok", "servico": "api-governo-simulada", "indisponibilidade": modo_indisponibilidade()})


@app.route("/api/governo/admin/indisponibilidade", methods=["GET", "POST"])
def admin_indisponibilidade():
    """POST {"modo": "off" | "503" | "timeout"} — simula indisponibilidade do serviço."""
    if request.method == "POST":
        modo = (request.get_json(silent=True) or {}).get("modo")
        if modo not in ("off", "503", "timeout"):
            return invalido(["modo deve ser 'off', '503' ou 'timeout'"])
        c = conn()
        c.execute("UPDATE configuracao SET valor=? WHERE chave='indisponibilidade'", (modo,))
        c.commit()
        c.close()
    return jsonify({"modo": modo_indisponibilidade()})


# ------------------------------------------------------------------ animais
def validar_animal(d):
    e = []
    if not re.fullmatch(r"\d{15}", str(d.get("microchip", ""))):
        e.append("microchip: 15 dígitos numéricos")
    for campo in ("nome", "especie", "tutor_nome"):
        if not d.get(campo):
            e.append(f"{campo}: obrigatório")
    if d.get("sexo") not in ("M", "F"):
        e.append("sexo: M ou F")
    if not cpf_valido(d.get("tutor_cpf")):
        e.append("tutor_cpf: inválido")
    return e


@app.post("/api/governo/animais")
def cadastrar_animal():
    d, c = request.get_json(silent=True) or {}, conn()
    try:
        r = replay(c)
        if r:
            return r
        erros = validar_animal(d)
        if erros:
            return invalido(erros)
        if c.execute("SELECT 1 FROM animal_gov WHERE microchip=?", (d["microchip"],)).fetchone():
            op = c.execute("SELECT protocolo FROM operacao WHERE tipo='CADASTRO_ANIMAL' AND microchip=?",
                           (d["microchip"],)).fetchone()
            return jsonify({"erro": "Microchip já cadastrado.", "protocolo_existente": op["protocolo"] if op else None}), 409
        c.execute("""INSERT INTO animal_gov (microchip,id_animal_origem,nome,especie,raca,sexo,data_nascimento,cor,
                     tutor_nome,tutor_cpf,responsavel_crmv,microchip_anterior,criado_em,atualizado_em)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (d["microchip"], d.get("id_animal_origem"), d["nome"], d["especie"], d.get("raca"), d["sexo"],
                   d.get("data_nascimento"), d.get("cor"), d["tutor_nome"], re.sub(r"\D", "", d["tutor_cpf"]),
                   d.get("responsavel_crmv"), d.get("microchip_anterior"), agora(), agora()))
        resp = registrar_op(c, "CADASTRO_ANIMAL", d["microchip"], {"mensagem": "Animal cadastrado.", "microchip": d["microchip"]})
        c.commit()
        return jsonify(resp), 201
    finally:
        c.close()


@app.get("/api/governo/animais")
def listar_animais():
    """Animais registrados: microchip e CPF do tutor em cada linha."""
    c = conn()
    try:
        return jsonify([dict(r) for r in c.execute(
            """SELECT microchip, nome, especie, tutor_nome, tutor_cpf, responsavel_crmv, criado_em
               FROM animal_gov ORDER BY criado_em DESC""")])
    finally:
        c.close()


@app.get("/api/governo/animais/<microchip>")
def consultar_animal(microchip):
    c = conn()
    try:
        a = c.execute("SELECT * FROM animal_gov WHERE microchip=?", (microchip,)).fetchone()
        if not a:
            return jsonify({"erro": "Animal não encontrado."}), 404
        vac = [dict(v) for v in c.execute("SELECT * FROM vacinacao_antirrabica WHERE microchip=? ORDER BY data_aplicacao",
                                          (microchip,))]
        return jsonify({**dict(a), "vacinacoes_antirrabicas": vac})
    finally:
        c.close()


@app.put("/api/governo/animais/<microchip>")
def atualizar_animal(microchip):
    d, c = request.get_json(silent=True) or {}, conn()
    try:
        r = replay(c)
        if r:
            return r
        if not c.execute("SELECT 1 FROM animal_gov WHERE microchip=?", (microchip,)).fetchone():
            return jsonify({"erro": "Animal não encontrado."}), 404
        d["microchip"] = microchip
        erros = validar_animal(d)
        if erros:
            return invalido(erros)
        c.execute("""UPDATE animal_gov SET nome=?,especie=?,raca=?,sexo=?,data_nascimento=?,cor=?,tutor_nome=?,
                     tutor_cpf=?,responsavel_crmv=?,atualizado_em=? WHERE microchip=?""",
                  (d["nome"], d["especie"], d.get("raca"), d["sexo"], d.get("data_nascimento"), d.get("cor"),
                   d["tutor_nome"], re.sub(r"\D", "", d["tutor_cpf"]), d.get("responsavel_crmv"), agora(), microchip))
        resp = registrar_op(c, "ATUALIZACAO_ANIMAL", microchip, {"mensagem": "Cadastro atualizado.", "microchip": microchip})
        c.commit()
        return jsonify(resp), 200
    finally:
        c.close()


# ------------------------------------------------------------------ vacinação antirrábica
@app.post("/api/governo/vacinacoes-antirrabicas")
def receber_vacinacao():
    d, c = request.get_json(silent=True) or {}, conn()
    try:
        r = replay(c)
        if r:
            return r
        erros = []
        if not re.fullmatch(r"\d{15}", str(d.get("microchip", ""))):
            erros.append("microchip: 15 dígitos numéricos")
        for campo in ("data_aplicacao", "vacina_nome", "fabricante", "lote", "veterinario_crmv"):
            if not d.get(campo):
                erros.append(f"{campo}: obrigatório")
        if d.get("tutor_cpf") and not cpf_valido(d["tutor_cpf"]):
            erros.append("tutor_cpf: inválido")
        if erros:
            return invalido(erros)
        # Independe de o animal já estar cadastrado no governo (regra de negócio 2)
        existente = c.execute("SELECT protocolo FROM vacinacao_antirrabica WHERE microchip=? AND data_aplicacao=? AND lote=?",
                              (d["microchip"], d["data_aplicacao"], d["lote"])).fetchone()
        if existente:                                  # mesma vacinação, chave diferente: não duplica
            return jsonify({"mensagem": "Vacinação já registrada.", "protocolo": existente["protocolo"],
                            "status": "PROCESSADO", "duplicado": True}), 200
        resp = registrar_op(c, "VACINA_ANTIRRABICA", d["microchip"],
                            {"mensagem": "Vacinação antirrábica registrada.", "microchip": d["microchip"]})
        c.execute("""INSERT INTO vacinacao_antirrabica (microchip,id_animal_origem,nome_animal,data_aplicacao,vacina_nome,
                     fabricante,lote,veterinario_nome,veterinario_crmv,tutor_nome,tutor_cpf,protocolo,criado_em)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (d["microchip"], d.get("id_animal_origem"), d.get("nome_animal"), d["data_aplicacao"], d["vacina_nome"],
                   d["fabricante"], d["lote"], d.get("veterinario_nome"), d["veterinario_crmv"], d.get("tutor_nome"),
                   re.sub(r"\D", "", d["tutor_cpf"]) if d.get("tutor_cpf") else None, resp["protocolo"], agora()))
        c.commit()
        return jsonify(resp), 201
    finally:
        c.close()


@app.get("/api/governo/operacoes/<protocolo>")
def consultar_operacao(protocolo):
    c = conn()
    try:
        op = c.execute("SELECT * FROM operacao WHERE protocolo=?", (protocolo,)).fetchone()
        if not op:
            return jsonify({"erro": "Protocolo não encontrado."}), 404
        cpf_tutor = None
        if op["tipo"] == "VACINA_ANTIRRABICA":
            v = c.execute("SELECT tutor_cpf FROM vacinacao_antirrabica WHERE protocolo=?", (protocolo,)).fetchone()
            cpf_tutor = v["tutor_cpf"] if v else None
        if not cpf_tutor:
            a = c.execute("SELECT tutor_cpf FROM animal_gov WHERE microchip=?", (op["microchip"],)).fetchone()
            cpf_tutor = a["tutor_cpf"] if a else None
        return jsonify({"protocolo": op["protocolo"], "tipo": op["tipo"], "microchip": op["microchip"],
                        "tutor_cpf": cpf_tutor, "status": op["status"], "criado_em": op["criado_em"]})
    finally:
        c.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, threaded=True)
