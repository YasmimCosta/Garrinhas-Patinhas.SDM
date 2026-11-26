"""Camada de acesso ao banco (SQLite)."""
import os
import sqlite3
from flask import g
import config


def connect():
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    """Cria o banco a partir de database/clinica/*.sql se ainda não existir."""
    if os.path.exists(config.DB_PATH):
        return
    conn = connect()
    for nome in ("01_schema.sql", "02_seed.sql"):
        with open(os.path.join(config.SQL_DIR, nome), encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.commit()
    conn.close()


def rows(cur):
    return [dict(r) for r in cur.fetchall()]


def one(cur):
    r = cur.fetchone()
    return dict(r) if r else None
