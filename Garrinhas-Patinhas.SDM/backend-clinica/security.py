"""Hash de senha, JWT e proteção de endpoints."""
import uuid
import datetime as dt
from functools import wraps

import jwt
from flask import request, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

import config
import db as dbm


def erro(status, msg, **extra):
    return jsonify({"erro": msg, **extra}), status


def hash_senha(senha):
    return generate_password_hash(senha)          # scrypt + salt


def confere_senha(hash_, senha):
    return check_password_hash(hash_, senha)


def gerar_token(vet):
    agora = dt.datetime.now(dt.timezone.utc)
    return jwt.encode(
        {"sub": str(vet["id_veterinario"]), "jti": uuid.uuid4().hex, "iat": agora,
         "exp": agora + dt.timedelta(minutes=config.JWT_EXPIRATION_MIN)},
        config.JWT_SECRET, algorithm="HS256")


def auth_required(f):
    """Exige token válido, não revogado, de veterinário ATIVO e com senha confirmada."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        cab = request.headers.get("Authorization", "")
        if not cab.startswith("Bearer "):
            return erro(401, "Autenticação necessária.")
        try:
            p = jwt.decode(cab[7:], config.JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return erro(401, "Sessão expirada.")
        except jwt.InvalidTokenError:
            return erro(401, "Token inválido.")
        db = dbm.get_db()
        if db.execute("SELECT 1 FROM token_revogado WHERE jti = ?", (p["jti"],)).fetchone():
            return erro(401, "Sessão encerrada.")
        vet = dbm.one(db.execute("SELECT * FROM veterinario WHERE id_veterinario = ?", (int(p["sub"]),)))
        if not vet or vet["situacao"] != "ATIVO":
            return erro(403, "Veterinário inativo.")
        if not vet["senha_confirmada"]:
            return erro(403, "Senha ainda não confirmada.")
        g.vet, g.jti = vet, p["jti"]
        return f(*args, **kwargs)
    return wrapper
