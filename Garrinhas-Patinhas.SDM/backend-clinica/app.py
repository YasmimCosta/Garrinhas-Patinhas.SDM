"""API privada da Clínica Veterinária (Flask). Execute: python app.py"""
import json
import secrets
import sqlite3
import datetime as dt

from flask import Flask, request, jsonify, g

import config
import db as dbm
import integracao
import viacep
from db import rows, one
from security import (auth_required, confere_senha, erro, gerar_token, hash_senha)
from validators import cpf_valido, data_iso, email_valido, microchip_valido, so_digitos

app = Flask(__name__)
app.teardown_appcontext(dbm.close_db)
dbm.init_db()


# ------------------------------------------------------------------ utilidades
@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return resp


@app.errorhandler(404)
def _404(_e):
    return erro(404, "Recurso não encontrado.")


@app.errorhandler(405)
def _405(_e):
    return erro(405, "Método não permitido.")


@app.errorhandler(Exception)
def _500(e):
    app.logger.exception(e)
    return erro(500, "Erro interno do servidor.")


def corpo():
    return request.get_json(silent=True) or {}


def faltam(d, campos):
    return [c for c in campos if d.get(c) in (None, "")]


def invalido(msg, **extra):
    return erro(422, msg, **extra)


def hoje():
    return dt.date.today().isoformat()


# ------------------------------------------------------------------ saúde
@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "servico": "api-clinica"})


# ------------------------------------------------------------------ autenticação (3.1)
@app.post("/api/auth/cadastro")
def cadastro_vet():
    d, db = corpo(), dbm.get_db()
    f = faltam(d, ["nome", "cpf", "crmv", "crmv_uf", "email", "senha"])
    if f:
        return invalido("Campos obrigatórios ausentes.", campos=f)
    if not cpf_valido(d["cpf"]):
        return invalido("CPF inválido.")
    if not email_valido(d["email"]):
        return invalido("E-mail inválido.")
    if len(d["senha"]) < 8:
        return invalido("A senha deve ter ao menos 8 caracteres.")
    codigo = f"{secrets.randbelow(10**6):06d}"
    try:
        cur = db.execute(
            """INSERT INTO veterinario (nome,cpf,crmv,crmv_uf,telefone,email,senha_hash,codigo_confirmacao)
               VALUES (?,?,?,?,?,?,?,?)""",
            (d["nome"], so_digitos(d["cpf"]), str(d["crmv"]), d["crmv_uf"].upper(), d.get("telefone"),
             d["email"].lower(), hash_senha(d["senha"]), codigo))
        db.commit()
    except sqlite3.IntegrityError:
        return erro(409, "CPF, e-mail ou CRMV já cadastrado.")
    print(f"[E-MAIL SIMULADO] para {d['email']}: código de confirmação = {codigo}")
    return jsonify({"id_veterinario": cur.lastrowid, "codigo_confirmacao_simulado": codigo,
                    "mensagem": "Envio de e-mail simulado: informe o código em /api/auth/confirmar."}), 201


@app.post("/api/auth/confirmar")
def confirmar_senha():
    d, db = corpo(), dbm.get_db()
    vet = one(db.execute("SELECT * FROM veterinario WHERE email = ?", (str(d.get("email", "")).lower(),)))
    if not vet or not vet["codigo_confirmacao"] or vet["codigo_confirmacao"] != str(d.get("codigo", "")):
        return invalido("E-mail ou código de confirmação inválido.")
    db.execute("""UPDATE veterinario SET senha_confirmada=1, confirmada_em=datetime('now'),
                  codigo_confirmacao=NULL WHERE id_veterinario=?""", (vet["id_veterinario"],))
    db.commit()
    return jsonify({"mensagem": "Senha confirmada. Já é possível fazer login."})


@app.post("/api/auth/login")
def login():
    d, db = corpo(), dbm.get_db()
    vet = one(db.execute("SELECT * FROM veterinario WHERE email = ?", (str(d.get("email", "")).lower(),)))
    if not vet or not confere_senha(vet["senha_hash"], str(d.get("senha", ""))):
        return erro(401, "E-mail ou senha incorretos.")
    if vet["situacao"] != "ATIVO":
        return erro(403, "Veterinário inativo. Acesso bloqueado.")
    if not vet["senha_confirmada"]:
        return erro(403, "Senha não confirmada. Confirme o código enviado ao e-mail.")
    db.execute("UPDATE veterinario SET ultimo_acesso = datetime('now') WHERE id_veterinario = ?",
               (vet["id_veterinario"],))
    db.commit()
    return jsonify({"token": gerar_token(vet),
                    "veterinario": {k: vet[k] for k in ("id_veterinario", "nome", "crmv", "crmv_uf", "email")}})


@app.post("/api/auth/logout")
@auth_required
def logout():
    db = dbm.get_db()
    db.execute("INSERT OR IGNORE INTO token_revogado (jti) VALUES (?)", (g.jti,))
    db.commit()
    return jsonify({"mensagem": "Sessão encerrada."})


@app.get("/api/auth/me")
@auth_required
def me():
    return jsonify({k: g.vet[k] for k in ("id_veterinario", "nome", "crmv", "crmv_uf", "email", "ultimo_acesso")})


# ------------------------------------------------------------------ CEP (3.3)
@app.get("/api/cep/<cep>")
@auth_required
def cep(cep):
    try:
        return jsonify(viacep.consultar(cep))
    except viacep.CepInvalido as e:
        return invalido(str(e))
    except viacep.CepNaoEncontrado as e:
        return erro(404, str(e), preenchimento_manual=True)
    except viacep.ViaCepIndisponivel as e:
        return erro(504 if e.timeout else 503, str(e), preenchimento_manual=True)


# ------------------------------------------------------------------ espécies e raças (3.4 / 3.5)
@app.get("/api/especies")
@auth_required
def listar_especies():
    return jsonify(rows(dbm.get_db().execute("SELECT * FROM especie WHERE situacao='ATIVO' ORDER BY nome")))


@app.post("/api/especies")
@auth_required
def criar_especie():
    d, db = corpo(), dbm.get_db()
    if faltam(d, ["nome"]):
        return invalido("Informe o nome da espécie.")
    try:
        cur = db.execute("INSERT INTO especie (nome, descricao) VALUES (?,?)", (d["nome"], d.get("descricao")))
        db.commit()
    except sqlite3.IntegrityError:
        return erro(409, "Espécie já cadastrada.")
    return jsonify({"id_especie": cur.lastrowid}), 201


@app.get("/api/racas")
@auth_required
def listar_racas():
    db, esp = dbm.get_db(), request.args.get("id_especie")
    sql, args = "SELECT * FROM raca WHERE situacao='ATIVO'", []
    if esp:
        sql, args = sql + " AND id_especie = ?", [esp]
    return jsonify(rows(db.execute(sql + " ORDER BY nome", args)))


@app.post("/api/racas")
@auth_required
def criar_raca():
    d, db = corpo(), dbm.get_db()
    if faltam(d, ["nome", "id_especie"]):
        return invalido("Informe nome e id_especie.")
    if not db.execute("SELECT 1 FROM especie WHERE id_especie=?", (d["id_especie"],)).fetchone():
        return invalido("Espécie inexistente.")
    try:
        cur = db.execute("INSERT INTO raca (id_especie,nome,porte,descricao) VALUES (?,?,?,?)",
                         (d["id_especie"], d["nome"], d.get("porte"), d.get("descricao")))
        db.commit()
    except sqlite3.IntegrityError:
        return erro(409, "Raça já cadastrada para esta espécie.")
    return jsonify({"id_raca": cur.lastrowid}), 201


# ------------------------------------------------------------------ tutores e endereços (3.2 / 3.3)
CAMPOS_END = ["cep", "logradouro", "numero", "bairro", "cidade", "uf"]


def _tutor_completo(db, id_tutor):
    t = one(db.execute("SELECT * FROM tutor WHERE id_tutor=?", (id_tutor,)))
    if t:
        t["endereco"] = one(db.execute("SELECT * FROM endereco WHERE id_endereco=?", (t["id_endereco"],)))
    return t


def _validar_tutor(d, parcial=False):
    if not parcial:
        f = faltam(d, ["nome", "cpf", "data_nascimento", "email", "telefone", "endereco"])
        if f:
            return f"Campos obrigatórios ausentes: {', '.join(f)}."
    if "cpf" in d and not cpf_valido(d["cpf"]):
        return "CPF inválido."
    if "email" in d and not email_valido(d["email"]):
        return "E-mail inválido."
    if "data_nascimento" in d:
        n = data_iso(d["data_nascimento"])
        if not n or str(n)[:10] > hoje():
            return "Data de nascimento inválida."
    e = d.get("endereco")
    if e is not None:
        f = faltam(e, CAMPOS_END)
        if f:
            return f"Endereço incompleto: {', '.join(f)}."
        if len(str(e["uf"])) != 2 or len(so_digitos(e["cep"])) != 8:
            return "CEP (8 dígitos) ou UF (2 letras) inválidos."
    return None


@app.post("/api/tutores")
@auth_required
def criar_tutor():
    d, db = corpo(), dbm.get_db()
    msg = _validar_tutor(d)
    if msg:
        return invalido(msg)
    cpf = so_digitos(d["cpf"])
    if db.execute("SELECT 1 FROM tutor WHERE cpf=?", (cpf,)).fetchone():
        return erro(409, "CPF já cadastrado para outro tutor.")
    e = d["endereco"]
    ce = db.execute("""INSERT INTO endereco (cep,logradouro,numero,complemento,bairro,cidade,uf,codigo_ibge)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (so_digitos(e["cep"]), e["logradouro"], e["numero"], e.get("complemento"), e["bairro"],
                     e["cidade"], e["uf"].upper(), e.get("codigo_ibge")))
    ct = db.execute("INSERT INTO tutor (id_endereco,nome,cpf,data_nascimento,telefone,email) VALUES (?,?,?,?,?,?)",
                    (ce.lastrowid, d["nome"], cpf, d["data_nascimento"], d["telefone"], d["email"]))
    db.commit()
    return jsonify(_tutor_completo(db, ct.lastrowid)), 201


@app.get("/api/tutores")
@auth_required
def listar_tutores():
    db, q = dbm.get_db(), f"%{request.args.get('q', '')}%"
    return jsonify(rows(db.execute(
        "SELECT id_tutor,nome,cpf,telefone,email,situacao FROM tutor WHERE nome LIKE ? ORDER BY nome", (q,))))


@app.get("/api/tutores/<int:id_tutor>")
@auth_required
def obter_tutor(id_tutor):
    t = _tutor_completo(dbm.get_db(), id_tutor)
    return jsonify(t) if t else erro(404, "Tutor não encontrado.")


@app.put("/api/tutores/<int:id_tutor>")
@auth_required
def alterar_tutor(id_tutor):
    d, db = corpo(), dbm.get_db()
    t = one(db.execute("SELECT * FROM tutor WHERE id_tutor=?", (id_tutor,)))
    if not t:
        return erro(404, "Tutor não encontrado.")
    msg = _validar_tutor(d, parcial=True)
    if msg:
        return invalido(msg)
    if "cpf" in d:
        d["cpf"] = so_digitos(d["cpf"])
        if db.execute("SELECT 1 FROM tutor WHERE cpf=? AND id_tutor<>?", (d["cpf"], id_tutor)).fetchone():
            return erro(409, "CPF já cadastrado para outro tutor.")
    for c in ("nome", "cpf", "data_nascimento", "telefone", "email", "situacao"):
        if c in d:
            if c == "situacao" and d[c] not in ("ATIVO", "INATIVO"):
                return invalido("Situação inválida.")
            db.execute(f"UPDATE tutor SET {c}=? WHERE id_tutor=?", (d[c], id_tutor))
    if d.get("endereco"):
        e = {**one(db.execute("SELECT * FROM endereco WHERE id_endereco=?", (t["id_endereco"],))), **d["endereco"]}
        db.execute("""UPDATE endereco SET cep=?,logradouro=?,numero=?,complemento=?,bairro=?,cidade=?,uf=?,
                      codigo_ibge=? WHERE id_endereco=?""",
                   (so_digitos(e["cep"]), e["logradouro"], e["numero"], e.get("complemento"), e["bairro"],
                    e["cidade"], e["uf"].upper(), e.get("codigo_ibge"), t["id_endereco"]))
    db.commit()
    return jsonify(_tutor_completo(db, id_tutor))


@app.delete("/api/tutores/<int:id_tutor>")
@auth_required
def inativar_tutor(id_tutor):                     # exclusão lógica
    db = dbm.get_db()
    cur = db.execute("UPDATE tutor SET situacao='INATIVO' WHERE id_tutor=?", (id_tutor,))
    db.commit()
    return jsonify({"mensagem": "Tutor inativado."}) if cur.rowcount else erro(404, "Tutor não encontrado.")


# ------------------------------------------------------------------ animais e microchip (3.7)
def _microchip_ativo(db, id_animal):
    return one(db.execute("""SELECT v.*, vt.nome AS veterinario_nome FROM vinculo_microchip v
                             JOIN veterinario vt USING (id_veterinario)
                             WHERE id_animal=? AND data_fim IS NULL""", (id_animal,)))


def _situacao_gov(db, id_animal):
    cad = one(db.execute("""SELECT status, protocolo_externo, mensagem_erro FROM integracao_governo
                            WHERE id_animal=? AND tipo_operacao IN ('CADASTRO_ANIMAL','ATUALIZACAO_ANIMAL')
                            ORDER BY id_integracao DESC LIMIT 1""", (id_animal,)))
    abertas = db.execute("SELECT COUNT(*) FROM integracao_governo WHERE id_animal=? AND status<>'CONFIRMADA'",
                         (id_animal,)).fetchone()[0]
    return {"cadastro_governo": cad["status"] if cad else "NAO_ENVIADO",
            "protocolo": cad["protocolo_externo"] if cad else None,
            "mensagem_erro": cad["mensagem_erro"] if cad else None,
            "comunicacoes_nao_confirmadas": abertas}


def _animal_completo(db, id_animal):
    a = one(db.execute("""SELECT a.*, t.nome AS tutor_nome, e.nome AS especie, r.nome AS raca
                          FROM animal a JOIN tutor t USING (id_tutor) JOIN especie e USING (id_especie)
                          LEFT JOIN raca r ON r.id_raca = a.id_raca WHERE a.id_animal=?""", (id_animal,)))
    if a:
        a["raca"] = a["raca"] or "Sem raça definida"
        a["microchip_ativo"] = _microchip_ativo(db, id_animal)
        a["integracao_governo"] = _situacao_gov(db, id_animal)
    return a


def _validar_animal(db, d, parcial=False):
    if not parcial:
        f = faltam(d, ["nome", "id_tutor", "id_especie", "sexo"])
        if f:
            return f"Campos obrigatórios ausentes: {', '.join(f)}."
        if not d.get("data_nascimento") and d.get("idade_estimada_meses") in (None, ""):
            return "Informe data_nascimento ou idade_estimada_meses."
    if "sexo" in d and d["sexo"] not in ("M", "F"):
        return "Sexo deve ser M ou F."
    if d.get("peso_atual") is not None and not (isinstance(d["peso_atual"], (int, float)) and d["peso_atual"] > 0):
        return "Peso atual deve ser um número positivo."
    if d.get("data_nascimento") and (not data_iso(d["data_nascimento"]) or d["data_nascimento"] > hoje()):
        return "Data de nascimento inválida."
    if "id_tutor" in d:
        t = db.execute("SELECT situacao FROM tutor WHERE id_tutor=?", (d["id_tutor"],)).fetchone()
        if not t or t["situacao"] != "ATIVO":
            return "Todo animal precisa de um tutor ATIVO existente."
    if "id_especie" in d and not db.execute("SELECT 1 FROM especie WHERE id_especie=?", (d["id_especie"],)).fetchone():
        return "Espécie inexistente."
    if d.get("id_raca"):
        r = db.execute("SELECT id_especie FROM raca WHERE id_raca=?", (d["id_raca"],)).fetchone()
        if not r:
            return "Raça inexistente."
        if "id_especie" in d and r["id_especie"] != d["id_especie"]:
            return "A raça selecionada não é compatível com a espécie informada."
    return None


@app.post("/api/animais")
@auth_required
def criar_animal():
    d, db = corpo(), dbm.get_db()
    msg = _validar_animal(db, d)
    if msg:
        return invalido(msg)
    cur = db.execute("""INSERT INTO animal (id_tutor,id_especie,id_raca,nome,data_nascimento,idade_estimada_meses,
                        sexo,cor,peso_atual,observacoes) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                     (d["id_tutor"], d["id_especie"], d.get("id_raca") or None, d["nome"], d.get("data_nascimento"),
                      d.get("idade_estimada_meses"), d["sexo"], d.get("cor"), d.get("peso_atual"), d.get("observacoes")))
    db.commit()
    return jsonify(_animal_completo(db, cur.lastrowid)), 201


@app.get("/api/animais")
@auth_required
def listar_animais():
    db, args, sql = dbm.get_db(), [], """SELECT a.id_animal,a.nome,a.sexo,a.situacao,t.nome AS tutor_nome,
        e.nome AS especie, COALESCE(r.nome,'Sem raça definida') AS raca,
        (SELECT codigo_microchip FROM vinculo_microchip v WHERE v.id_animal=a.id_animal AND data_fim IS NULL) AS microchip
        FROM animal a JOIN tutor t USING(id_tutor) JOIN especie e USING(id_especie)
        LEFT JOIN raca r ON r.id_raca=a.id_raca WHERE 1=1"""
    if request.args.get("id_tutor"):
        sql, args = sql + " AND a.id_tutor=?", args + [request.args["id_tutor"]]
    if request.args.get("q"):
        sql, args = sql + " AND a.nome LIKE ?", args + [f"%{request.args['q']}%"]
    return jsonify(rows(db.execute(sql + " ORDER BY a.nome", args)))


@app.get("/api/animais/<int:id_animal>")
@auth_required
def obter_animal(id_animal):
    a = _animal_completo(dbm.get_db(), id_animal)
    return jsonify(a) if a else erro(404, "Animal não encontrado.")


def _payload_animal(db, id_animal, chip, anterior=None):
    a = _animal_completo(db, id_animal)
    t = _tutor_completo(db, a["id_tutor"])
    v = one(db.execute("SELECT nome,crmv,crmv_uf FROM veterinario WHERE id_veterinario=?", (chip["id_veterinario"],)))
    return {"microchip": chip["codigo_microchip"], "id_animal_origem": id_animal, "nome": a["nome"],
            "especie": a["especie"], "raca": a["raca"], "sexo": a["sexo"], "data_nascimento": a["data_nascimento"],
            "cor": a["cor"], "tutor_nome": t["nome"], "tutor_cpf": t["cpf"],
            "responsavel_crmv": f"{v['crmv']}/{v['crmv_uf']}", "microchip_anterior": anterior}


@app.put("/api/animais/<int:id_animal>")
@auth_required
def alterar_animal(id_animal):
    d, db = corpo(), dbm.get_db()
    if not db.execute("SELECT 1 FROM animal WHERE id_animal=?", (id_animal,)).fetchone():
        return erro(404, "Animal não encontrado.")
    atual = one(db.execute("SELECT id_especie FROM animal WHERE id_animal=?", (id_animal,)))
    msg = _validar_animal(db, {**({"id_especie": atual["id_especie"]} if d.get("id_raca") else {}), **d}, parcial=True)
    if msg:
        return invalido(msg)
    for c in ("nome", "id_tutor", "id_especie", "id_raca", "data_nascimento", "idade_estimada_meses", "sexo",
              "cor", "peso_atual", "observacoes", "situacao"):
        if c in d:
            if c == "situacao" and d[c] not in ("ATIVO", "INATIVO", "OBITO"):
                return invalido("Situação inválida.")
            db.execute(f"UPDATE animal SET {c}=? WHERE id_animal=?", (d[c] or None if c == "id_raca" else d[c], id_animal))
    db.commit()
    chip = _microchip_ativo(db, id_animal)
    if chip:                                           # mantém o cadastro governamental atualizado
        i = integracao.criar(db, id_animal, "ATUALIZACAO_ANIMAL", _payload_animal(db, id_animal, chip))
        integracao.processar(db, i)
    return jsonify(_animal_completo(db, id_animal))


@app.delete("/api/animais/<int:id_animal>")
@auth_required
def inativar_animal(id_animal):
    db = dbm.get_db()
    cur = db.execute("UPDATE animal SET situacao='INATIVO' WHERE id_animal=?", (id_animal,))
    db.commit()
    return jsonify({"mensagem": "Animal inativado."}) if cur.rowcount else erro(404, "Animal não encontrado.")


@app.post("/api/animais/<int:id_animal>/microchip")
@auth_required
def vincular_microchip(id_animal):
    d, db = corpo(), dbm.get_db()
    a = one(db.execute("SELECT * FROM animal WHERE id_animal=?", (id_animal,)))
    if not a:
        return erro(404, "Animal não encontrado.")
    if a["situacao"] != "ATIVO":
        return invalido("Animal não está ativo.")
    codigo = str(d.get("codigo_microchip", ""))
    if not microchip_valido(codigo):
        return invalido("Microchip deve ter 15 dígitos numéricos.")
    if db.execute("SELECT 1 FROM vinculo_microchip WHERE codigo_microchip=?", (codigo,)).fetchone():
        return erro(409, "Microchip já utilizado (vinculado a este ou a outro animal).")
    anterior = _microchip_ativo(db, id_animal)
    try:
        if anterior:                                   # substituição: preserva o histórico
            db.execute("""UPDATE vinculo_microchip SET data_fim=datetime('now'), motivo_fim=?
                          WHERE id_vinculo=?""", (d.get("motivo") or "SUBSTITUICAO", anterior["id_vinculo"]))
        cur = db.execute("""INSERT INTO vinculo_microchip (id_animal,id_veterinario,codigo_microchip,observacao)
                            VALUES (?,?,?,?)""", (id_animal, g.vet["id_veterinario"], codigo, d.get("observacao")))
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return erro(409, "Microchip já utilizado.")
    chip = one(db.execute("SELECT * FROM vinculo_microchip WHERE id_vinculo=?", (cur.lastrowid,)))
    i = integracao.criar(db, id_animal, "CADASTRO_ANIMAL",
                         _payload_animal(db, id_animal, chip, anterior["codigo_microchip"] if anterior else None))
    integracao.processar(db, i)
    return jsonify({"vinculo": chip, "substituiu": anterior["codigo_microchip"] if anterior else None,
                    "integracao_governo": _situacao_gov(db, id_animal)}), 201


@app.get("/api/animais/<int:id_animal>/microchips")
@auth_required
def historico_microchips(id_animal):
    return jsonify(rows(dbm.get_db().execute("""SELECT v.*, vt.nome AS veterinario_nome FROM vinculo_microchip v
        JOIN veterinario vt USING(id_veterinario) WHERE id_animal=? ORDER BY id_vinculo DESC""", (id_animal,))))


# ------------------------------------------------------------------ consultas (3.8)
@app.post("/api/consultas")
@auth_required
def criar_consulta():
    d, db = corpo(), dbm.get_db()
    f = faltam(d, ["id_animal", "data_hora", "motivo"])
    if f:
        return invalido(f"Campos obrigatórios ausentes: {', '.join(f)}.")
    if not db.execute("SELECT 1 FROM animal WHERE id_animal=?", (d["id_animal"],)).fetchone():
        return invalido("Animal inexistente.")
    if not data_iso(d["data_hora"]):
        return invalido("data_hora inválida (use AAAA-MM-DDTHH:MM).")
    status = d.get("status", "REALIZADA")
    if status not in ("AGENDADA", "REALIZADA", "CANCELADA", "NAO_COMPARECEU"):
        return invalido("Situação da consulta inválida.")
    if d.get("temperatura") not in (None, "") and not (30 <= float(d["temperatura"]) <= 45):
        return invalido("Temperatura fora da faixa plausível (30–45 °C).")
    if d.get("peso") not in (None, "") and float(d["peso"]) <= 0:
        return invalido("Peso inválido.")
    cur = db.execute("""INSERT INTO consulta (id_animal,id_veterinario,data_hora,motivo,anamnese,sintomas,diagnostico,
        tratamento,prescricao,peso,temperatura,observacoes,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (d["id_animal"], g.vet["id_veterinario"], d["data_hora"], d["motivo"], d.get("anamnese"),
                      d.get("sintomas"), d.get("diagnostico"), d.get("tratamento"), d.get("prescricao"),
                      d.get("peso") or None, d.get("temperatura") or None, d.get("observacoes"), status))
    if status == "REALIZADA" and d.get("peso"):        # mantém o peso atual do animal
        db.execute("UPDATE animal SET peso_atual=? WHERE id_animal=?", (d["peso"], d["id_animal"]))
    db.commit()
    return jsonify(one(db.execute("SELECT * FROM consulta WHERE id_consulta=?", (cur.lastrowid,)))), 201


@app.get("/api/animais/<int:id_animal>/consultas")
@auth_required
def historico_consultas(id_animal):
    return jsonify(rows(dbm.get_db().execute("""SELECT c.*, v.nome AS veterinario_nome FROM consulta c
        JOIN veterinario v USING(id_veterinario) WHERE id_animal=? ORDER BY data_hora DESC""", (id_animal,))))


# ------------------------------------------------------------------ vacinas + regra da antirrábica (3.9 / 4)
TIPOS_VACINA = ("ANTIRRABICA", "POLIVALENTE", "GRIPE", "GIARDIA", "OUTRA")


def _comunicar_antirrabica(db, id_vacina):
    """Após o registro local, cria e tenta enviar a comunicação obrigatória ao governo."""
    v = one(db.execute("SELECT * FROM vacina WHERE id_vacina=?", (id_vacina,)))
    a = one(db.execute("SELECT nome FROM animal WHERE id_animal=?", (v["id_animal"],)))
    chip = _microchip_ativo(db, v["id_animal"])
    vet = one(db.execute("SELECT nome,crmv,crmv_uf FROM veterinario WHERE id_veterinario=?", (v["id_veterinario"],)))
    payload = {"microchip": chip["codigo_microchip"], "id_animal_origem": v["id_animal"], "nome_animal": a["nome"],
               "data_aplicacao": v["data_aplicacao"], "vacina_nome": v["nome"], "fabricante": v["fabricante"],
               "lote": v["lote"], "veterinario_nome": vet["nome"], "veterinario_crmv": f"{vet['crmv']}/{vet['crmv_uf']}"}
    i = integracao.criar(db, v["id_animal"], "VACINA_ANTIRRABICA", payload, id_vacina=id_vacina,
                         chave=f"VACINA_ANTIRRABICA-{id_vacina}")        # chave fixa => idempotente
    return dict(integracao.processar(db, i))


@app.post("/api/vacinas")
@auth_required
def criar_vacina():
    d, db = corpo(), dbm.get_db()
    f = faltam(d, ["id_animal", "nome", "tipo", "fabricante", "lote", "data_aplicacao"])
    if f:
        return invalido(f"Campos obrigatórios ausentes: {', '.join(f)}.")
    if d["tipo"] not in TIPOS_VACINA:
        return invalido(f"Tipo de vacina inválido. Use: {', '.join(TIPOS_VACINA)}.")
    status = d.get("status", "APLICADA")
    if status not in ("AGENDADA", "APLICADA", "CANCELADA"):
        return invalido("Situação da vacina inválida.")
    if not db.execute("SELECT 1 FROM animal WHERE id_animal=?", (d["id_animal"],)).fetchone():
        return invalido("Animal inexistente.")
    if not data_iso(d["data_aplicacao"]):
        return invalido("data_aplicacao inválida.")
    if status == "APLICADA" and d.get("validade_lote") and d["validade_lote"] < str(d["data_aplicacao"])[:10]:
        return invalido("Lote vencido: validade anterior à data de aplicação.")
    if d.get("proxima_dose") and d["proxima_dose"] <= str(d["data_aplicacao"])[:10]:
        return invalido("A próxima dose deve ser posterior à data de aplicação.")
    antirrabica = 1 if d["tipo"] == "ANTIRRABICA" else 0
    if antirrabica and status == "APLICADA" and not _microchip_ativo(db, d["id_animal"]):
        return invalido("Vacina antirrábica exige animal com microchip vinculado (necessário para a comunicação).")
    cur = db.execute("""INSERT INTO vacina (id_animal,id_veterinario,id_consulta,nome,tipo,antirrabica,fabricante,lote,
        data_aplicacao,dose,via_aplicacao,proxima_dose,validade_lote,observacoes,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (d["id_animal"], g.vet["id_veterinario"], d.get("id_consulta"), d["nome"], d["tipo"], antirrabica,
                      d["fabricante"], d["lote"], d["data_aplicacao"], d.get("dose"), d.get("via_aplicacao"),
                      d.get("proxima_dose"), d.get("validade_lote"), d.get("observacoes"), status))
    db.commit()                                       # 1) registro local sempre persiste
    integ = _comunicar_antirrabica(db, cur.lastrowid) if antirrabica and status == "APLICADA" else None  # 2) comunicação
    return jsonify({"vacina": one(db.execute("SELECT * FROM vacina WHERE id_vacina=?", (cur.lastrowid,))),
                    "comunicacao_governo": integ}), 201


@app.patch("/api/vacinas/<int:id_vacina>/aplicar")
@auth_required
def aplicar_vacina(id_vacina):
    """Vacina AGENDADA -> APLICADA (dispara a comunicação se antirrábica)."""
    db = dbm.get_db()
    v = one(db.execute("SELECT * FROM vacina WHERE id_vacina=?", (id_vacina,)))
    if not v:
        return erro(404, "Vacina não encontrada.")
    if v["status"] != "AGENDADA":
        return invalido("Apenas vacinas AGENDADAS podem ser aplicadas.")
    if v["antirrabica"] and not _microchip_ativo(db, v["id_animal"]):
        return invalido("Vacina antirrábica exige animal com microchip vinculado.")
    db.execute("UPDATE vacina SET status='APLICADA', data_aplicacao=?, id_veterinario=? WHERE id_vacina=?",
               (hoje(), g.vet["id_veterinario"], id_vacina))
    db.commit()
    integ = _comunicar_antirrabica(db, id_vacina) if v["antirrabica"] else None
    return jsonify({"vacina": one(db.execute("SELECT * FROM vacina WHERE id_vacina=?", (id_vacina,))),
                    "comunicacao_governo": integ})


@app.get("/api/animais/<int:id_animal>/vacinas")
@auth_required
def historico_vacinas(id_animal):
    db = dbm.get_db()
    hist = rows(db.execute("""SELECT v.*, vt.nome AS veterinario_nome, i.id_integracao,
            i.status AS comunicacao_status, i.protocolo_externo AS comunicacao_protocolo
            FROM vacina v JOIN veterinario vt USING(id_veterinario)
            LEFT JOIN integracao_governo i ON i.id_vacina = v.id_vacina
            WHERE v.id_animal=? ORDER BY v.data_aplicacao DESC, v.id_vacina DESC""", (id_animal,)))
    prox = [{"id_vacina": v["id_vacina"], "nome": v["nome"], "proxima_dose": v["proxima_dose"],
             "atrasada": v["proxima_dose"] < hoje()}
            for v in sorted(hist, key=lambda x: x["proxima_dose"] or "9999")
            if v["proxima_dose"] and v["status"] == "APLICADA"]
    return jsonify({"historico": hist, "proximas_doses": prox})


# ------------------------------------------------------------------ controle das integrações (5)
@app.get("/api/integracoes")
@auth_required
def listar_integracoes():
    db, sql, args = dbm.get_db(), "SELECT * FROM integracao_governo WHERE 1=1", []
    for campo in ("status", "id_animal", "tipo_operacao"):
        if request.args.get(campo):
            sql, args = sql + f" AND {campo}=?", args + [request.args[campo]]
    return jsonify(rows(db.execute(sql + " ORDER BY id_integracao DESC", args)))


@app.get("/api/integracoes/<int:id_integracao>")
@auth_required
def obter_integracao(id_integracao):
    i = one(dbm.get_db().execute("SELECT * FROM integracao_governo WHERE id_integracao=?", (id_integracao,)))
    return jsonify(i) if i else erro(404, "Integração não encontrada.")


@app.post("/api/integracoes/<int:id_integracao>/reenviar")
@auth_required
def reenviar(id_integracao):
    db = dbm.get_db()
    if not db.execute("SELECT 1 FROM integracao_governo WHERE id_integracao=?", (id_integracao,)).fetchone():
        return erro(404, "Integração não encontrada.")
    return jsonify(dict(integracao.processar(db, id_integracao)))


@app.post("/api/integracoes/reprocessar-pendentes")
@auth_required
def reprocessar():
    ids = integracao.reprocessar_pendentes(dbm.get_db())
    return jsonify({"reprocessadas": ids})


if __name__ == "__main__":
    integracao.iniciar_reenvio_automatico()
    app.run(host="0.0.0.0", port=config.PORT, threaded=True)
