"""Diagnóstico de execução do CineRepertório. Execute: python diagnostico.py"""
from __future__ import annotations
import importlib.util
import os
import sqlite3
import sys
import traceback
from pathlib import Path

BASE = Path(__file__).resolve().parent
falhas = 0

def check(rotulo, ok, detalhe=""):
    global falhas
    print(("[OK] " if ok else "[ERRO] ") + rotulo + (f" — {detalhe}" if detalhe else ""))
    if not ok:
        falhas += 1

print("=== AMBIENTE PYTHON ===")
print("Executável:", sys.executable)
print("Versão:", sys.version.split()[0])
flask_instalado = importlib.util.find_spec("flask") is not None
check("Flask instalado neste mesmo Python", flask_instalado,
      "execute 'python -m pip install -r requirements.txt' se estiver ausente")

print("\n=== ARQUIVOS DO PROJETO ===")
for relativo in ["app.py", "banco.py", "contas.py", "ia.py", "requirements.txt", "templates/base.html", "templates/notificacoes.html", "static/img/assistente-cinema.jpg", "banco.db"]:
    check(f"Arquivo {relativo}", (BASE / relativo).is_file())

print("\n=== BANCO SQLITE ===")
db = BASE / "banco.db"
try:
    con = sqlite3.connect(db)
    integridade = con.execute("PRAGMA integrity_check").fetchone()[0]
    erros_fk = con.execute("PRAGMA foreign_key_check").fetchall()
    tabelas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    total_filmes = con.execute("SELECT COUNT(*) FROM filmes").fetchone()[0] if "filmes" in tabelas else 0
    check("Integridade SQLite", integridade == "ok", integridade)
    check("Tabelas essenciais", {"filmes", "temas", "filme_temas", "usuarios", "anotacoes"}.issubset(tabelas))
    check("Catálogo com 112 filmes", total_filmes == 112, str(total_filmes))
    check("Chaves estrangeiras", not erros_fk, str(erros_fk[:3]))
    con.close()
except Exception as exc:
    check("Abertura do banco SQLite", False, str(exc))

print("\n=== SMTP ===")
variaveis_env = {}
arquivo_env = BASE / ".env"
if arquivo_env.is_file():
    for linha in arquivo_env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            variaveis_env[chave.strip()] = valor.strip().strip('"').strip("'")
smtp_chaves = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD"]
if all(os.environ.get(key) or variaveis_env.get(key) for key in smtp_chaves):
    print("[OK] Variáveis SMTP essenciais configuradas")
else:
    print("[AVISO] SMTP não configurado por completo; o site inicia, mas o formulário não enviará e-mails reais.")

if flask_instalado:
    print("\n=== INICIALIZAÇÃO FLASK ===")
    try:
        import app as aplicacao
        cliente = aplicacao.app.test_client()
        for rota in ["/", "/filmes", "/notificacoes"]:
            resposta = cliente.get(rota)
            check(f"GET {rota}", resposta.status_code == 200, f"HTTP {resposta.status_code}")
    except Exception as exc:
        check("Importação e inicialização do Flask", False, repr(exc))
        traceback.print_exc()
else:
    print("\nTestes HTTP não executados: Flask não está instalado neste interpretador.")

print(f"\nResultado do diagnóstico: {falhas} erro(s).")
sys.exit(1 if falhas else 0)
