"""
CineRepertório — conexão com o banco de dados SQLite (banco.db).

Centraliza a abertura da conexão, a criação das tabelas (sql/schema.sql)
e uma função auxiliar de contagem. Usado por app.py e contas.py.
"""



import os
import sqlite3

from flask import g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE", os.path.join(BASE_DIR, "banco.db"))
SCHEMA_SQL = os.path.join(BASE_DIR, "sql", "schema.sql")

TABELAS = {"filmes", "temas", "filme_temas", "usuarios", "anotacoes"}


def conectar():
    """Abre uma conexão com linhas acessíveis por nome de coluna."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")  # ativa as chaves estrangeiras
    # Usada nas buscas para ignorar maiúsculas/minúsculas em português.
    con.create_function("minusc", 1, lambda s: s.lower() if isinstance(s, str) else s)
    return con


def get_db():
    """Uma conexão por requisição, reaproveitada dentro dela."""
    if "db" not in g:
        g.db = conectar()
    return g.db


def fechar_db(_erro=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def iniciar_banco():
    """Cria as tabelas caso o arquivo do banco ainda não as tenha."""
    con = conectar()
    with open(SCHEMA_SQL, encoding="utf-8") as arquivo:
        con.executescript(arquivo.read())
    con.close()


def contar(tabela):
    if tabela not in TABELAS:
        raise ValueError("Tabela inválida")
    return get_db().execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
