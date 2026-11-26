"""
Serviço de integração com a API governamental simulada.

Regras (enunciado, seção 4 e 5):
  * o registro local SEMPRE é gravado antes; a comunicação é uma operação separada;
  * situação: PENDENTE -> ENVIADA -> CONFIRMADA | FALHA;
  * indisponibilidade/timeout => PENDENTE (reenvio automático ou manual);
  * a chave de idempotência é fixa por operação, então reenviar não duplica no governo.
"""
import json
import time
import uuid
import threading
import datetime as dt

import requests
import config
import db as dbm


def agora():
    return dt.datetime.now().isoformat(timespec="seconds")


def criar(conn, id_animal, tipo, payload, id_vacina=None, chave=None):
    chave = chave or f"{tipo}-{uuid.uuid4().hex}"
    cur = conn.execute(
        """INSERT INTO integracao_governo
           (id_animal, id_vacina, tipo_operacao, chave_idempotencia, solicitacao_json, status, solicitado_em)
           VALUES (?,?,?,?,?, 'PENDENTE', ?)""",
        (id_animal, id_vacina, tipo, chave, json.dumps(payload, ensure_ascii=False), agora()))
    conn.commit()
    return cur.lastrowid


def _chamar(tipo, payload, chave):
    base = config.GOVERNO_API_URL.rstrip("/") + "/api/governo"
    h = {"Idempotency-Key": chave, "X-API-Key": config.GOVERNO_API_KEY}
    t = config.INTEGRACAO_TIMEOUT
    if tipo == "CADASTRO_ANIMAL":
        return requests.post(f"{base}/animais", json=payload, headers=h, timeout=t)
    if tipo == "ATUALIZACAO_ANIMAL":
        r = requests.put(f"{base}/animais/{payload['microchip']}", json=payload, headers=h, timeout=t)
        if r.status_code == 404:                      # ainda não existe no governo: cadastra
            r = requests.post(f"{base}/animais", json=payload, headers=h, timeout=t)
        return r
    if tipo == "VACINA_ANTIRRABICA":
        return requests.post(f"{base}/vacinacoes-antirrabicas", json=payload, headers=h, timeout=t)
    raise ValueError(f"Tipo de operação desconhecido: {tipo}")


def processar(conn, id_integracao):
    """Tenta enviar uma integração. Nunca levanta exceção de rede: grava o resultado."""
    row = conn.execute("SELECT * FROM integracao_governo WHERE id_integracao = ?", (id_integracao,)).fetchone()
    if row is None or row["status"] == "CONFIRMADA":
        return row
    tentativas = row["tentativas"] + 1
    conn.execute("UPDATE integracao_governo SET status='ENVIADA', tentativas=?, solicitado_em=? WHERE id_integracao=?",
                 (tentativas, agora(), id_integracao))
    conn.commit()

    status, protocolo, resposta, erro = "PENDENTE", row["protocolo_externo"], None, None
    try:
        r = _chamar(row["tipo_operacao"], json.loads(row["solicitacao_json"]), row["chave_idempotencia"])
        try:
            corpo = r.json()
        except ValueError:
            corpo = {"raw": r.text[:300]}
        resposta = json.dumps(corpo, ensure_ascii=False)
        if r.status_code in (200, 201):
            status, protocolo = "CONFIRMADA", corpo.get("protocolo")
        elif r.status_code >= 500 or r.status_code == 429:
            erro = f"Governo indisponível (HTTP {r.status_code})."
        else:                                          # 4xx: rejeitado, repetir igual não resolve
            status, erro = "FALHA", f"Rejeitado pelo governo (HTTP {r.status_code}): {corpo.get('erro', '')}"
    except requests.Timeout:
        erro = "Timeout na comunicação com o governo."
    except requests.RequestException:
        erro = "Governo inacessível (falha de conexão)."

    if status == "PENDENTE" and tentativas >= config.INTEGRACAO_MAX_TENTATIVAS:
        status, erro = "FALHA", f"{erro} Limite de {config.INTEGRACAO_MAX_TENTATIVAS} tentativas atingido."
    conn.execute("""UPDATE integracao_governo SET status=?, protocolo_externo=?, resposta_json=?,
                    respondido_em=?, mensagem_erro=? WHERE id_integracao=?""",
                 (status, protocolo, resposta, agora(), erro, id_integracao))
    conn.commit()
    return conn.execute("SELECT * FROM integracao_governo WHERE id_integracao = ?", (id_integracao,)).fetchone()


def reprocessar_pendentes(conn):
    """Reenvia PENDENTES e ENVIADAS 'esquecidas' (ex.: queda no meio do envio)."""
    corte = (dt.datetime.now() - dt.timedelta(seconds=60)).isoformat(timespec="seconds")
    ids = [r["id_integracao"] for r in conn.execute(
        """SELECT id_integracao FROM integracao_governo
           WHERE status='PENDENTE' OR (status='ENVIADA' AND solicitado_em < ?)
           ORDER BY id_integracao""", (corte,))]
    for i in ids:
        processar(conn, i)
    return ids


def iniciar_reenvio_automatico():
    if config.REENVIO_AUTOMATICO_S <= 0:
        return None

    def loop():
        while True:
            time.sleep(config.REENVIO_AUTOMATICO_S)
            try:
                conn = dbm.connect()
                reprocessar_pendentes(conn)
                conn.close()
            except Exception as e:           # a thread nunca pode morrer
                print("[reenvio automático] erro:", e)

    t = threading.Thread(target=loop, daemon=True, name="reenvio-governo")
    t.start()
    return t
