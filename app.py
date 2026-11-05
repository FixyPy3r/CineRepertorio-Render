"""
CineRepertório — UC35: Projeto Integrador Back-end
Aplicação web de repertórios socioculturais (filmes) para a redação do ENEM.

Armazenamento: banco relacional SQLite (banco.db), com as tabelas
filmes, temas, filme_temas e anotacoes (relacionadas por chave estrangeira).
Operações: CRUD completo de filmes e de anotações de repertório,
consultas com JOIN e rotas que devolvem JSON (API).
"""

import os
import re
import sqlite3
import unicodedata
from datetime import datetime
from urllib.parse import quote_plus

from flask import Flask, flash, g, jsonify, redirect, render_template, request, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE", os.path.join(BASE_DIR, "banco.db"))
SCHEMA_SQL = os.path.join(BASE_DIR, "sql", "schema.sql")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cinerepertorio-uc35")

PARTES = ["introducao", "desenvolvimento", "conclusao"]
ROTULO_PARTE = {
    "introducao": "Introdução",
    "desenvolvimento": "Desenvolvimento",
    "conclusao": "Conclusão",
}
COR_PADRAO = "from-amber-500/30 to-slate-900/60"


# --------------------------------------------------------------------------
# Camada de persistência (SQLite)
# --------------------------------------------------------------------------
def conectar():
    """Abre uma conexão com o banco, com linhas acessíveis por nome de coluna."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")  # ativa as chaves estrangeiras
    # Função usada nas buscas para ignorar maiúsculas/minúsculas em português.
    con.create_function("minusc", 1, lambda s: s.lower() if isinstance(s, str) else s)
    return con


def get_db():
    """Uma conexão por requisição, reaproveitada dentro dela."""
    if "db" not in g:
        g.db = conectar()
    return g.db


@app.teardown_appcontext
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


def _para_dict(linha, temas):
    """Converte uma linha do banco no dicionário usado pelos templates."""
    return {
        "id": linha["id"],
        "titulo": linha["titulo"],
        "ano": linha["ano"],
        "diretor": linha["diretor"],
        "imdb": linha["imdb"],
        "temas": temas,
        "sinopse": linha["sinopse"],
        "comoUsar": linha["como_usar"] or "",
        "citacao": linha["citacao"],
        "parte": linha["parte"],
        "cor": linha["cor"] or COR_PADRAO,
        "cartaz": linha["cartaz"] or "",
    }


def _temas_por_filme():
    """JOIN filme_temas x temas: devolve {filme_id: [nomes dos temas]}."""
    linhas = get_db().execute(
        """
        SELECT ft.filme_id, t.nome
        FROM filme_temas ft
        JOIN temas t ON t.id = ft.tema_id
        ORDER BY ft.rowid
        """
    ).fetchall()
    mapa = {}
    for linha in linhas:
        mapa.setdefault(linha["filme_id"], []).append(linha["nome"])
    return mapa


def consultar_filmes(busca="", tema="", parte="", ordem="imdb"):
    """Lista filmes aplicando busca, filtro por tema/parágrafo e ordenação (SQL)."""
    condicoes, parametros = [], []
    if busca:
        condicoes.append(
            """(instr(minusc(f.titulo), ?) > 0
                OR instr(minusc(f.diretor), ?) > 0
                OR EXISTS (SELECT 1
                           FROM filme_temas ft
                           JOIN temas t ON t.id = ft.tema_id
                           WHERE ft.filme_id = f.id AND instr(minusc(t.nome), ?) > 0))"""
        )
        parametros += [busca.lower()] * 3
    if tema:
        condicoes.append(
            """EXISTS (SELECT 1
                      FROM filme_temas ft
                      JOIN temas t ON t.id = ft.tema_id
                      WHERE ft.filme_id = f.id AND t.nome = ?)"""
        )
        parametros.append(tema)
    if parte:
        condicoes.append("f.parte = ?")
        parametros.append(parte)

    ordenacoes = {
        "ano": "f.ano DESC, f.titulo",
        "titulo": "minusc(f.titulo)",
        "imdb": "f.imdb DESC, f.titulo",
    }
    sql = "SELECT f.* FROM filmes f"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)
    sql += " ORDER BY " + ordenacoes.get(ordem, ordenacoes["imdb"])

    linhas = get_db().execute(sql, parametros).fetchall()
    temas = _temas_por_filme()
    return [_para_dict(l, temas.get(l["id"], [])) for l in linhas]


def listar_filmes():
    return consultar_filmes()


def buscar_filme(filme_id):
    linha = get_db().execute("SELECT * FROM filmes WHERE id = ?", (filme_id,)).fetchone()
    if linha is None:
        return None
    temas = [
        t["nome"]
        for t in get_db().execute(
            """
            SELECT t.nome
            FROM filme_temas ft
            JOIN temas t ON t.id = ft.tema_id
            WHERE ft.filme_id = ?
            ORDER BY ft.rowid
            """,
            (filme_id,),
        )
    ]
    return _para_dict(linha, temas)


def filmes_relacionados(filme_id, limite=6):
    """Filmes que compartilham temas com o filme informado (JOIN + GROUP BY)."""
    ids = [
        l["id"]
        for l in get_db().execute(
            """
            SELECT f.id
            FROM filmes f
            JOIN filme_temas ft ON ft.filme_id = f.id
            WHERE f.id <> :id
              AND ft.tema_id IN (SELECT tema_id FROM filme_temas WHERE filme_id = :id)
            GROUP BY f.id
            ORDER BY COUNT(*) DESC, f.imdb DESC
            LIMIT :limite
            """,
            {"id": filme_id, "limite": limite},
        )
    ]
    temas = _temas_por_filme()
    resultado = []
    for fid in ids:
        linha = get_db().execute("SELECT * FROM filmes WHERE id = ?", (fid,)).fetchone()
        resultado.append(_para_dict(linha, temas.get(fid, [])))
    return resultado


def temas_disponiveis():
    linhas = get_db().execute(
        """
        SELECT DISTINCT t.nome
        FROM temas t
        JOIN filme_temas ft ON ft.tema_id = t.id
        ORDER BY minusc(t.nome)
        """
    ).fetchall()
    return [l["nome"] for l in linhas]


def ids_de_filmes():
    return {l["id"] for l in get_db().execute("SELECT id FROM filmes")}


def salvar_filme(filme, criar):
    """INSERT (criar=True) ou UPDATE de um filme, regravando seus temas."""
    db = get_db()
    with db:  # transação: tudo ou nada
        if criar:
            db.execute(
                """INSERT INTO filmes
                   (id, titulo, ano, diretor, imdb, sinopse, como_usar, citacao, parte, cor, cartaz)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (filme["id"], filme["titulo"], filme["ano"], filme["diretor"], filme["imdb"],
                 filme["sinopse"], filme["comoUsar"], filme["citacao"], filme["parte"],
                 filme["cor"], filme["cartaz"]),
            )
        else:
            db.execute(
                """UPDATE filmes
                   SET titulo=?, ano=?, diretor=?, imdb=?, sinopse=?, como_usar=?,
                       citacao=?, parte=?, cor=?, cartaz=?
                   WHERE id=?""",
                (filme["titulo"], filme["ano"], filme["diretor"], filme["imdb"],
                 filme["sinopse"], filme["comoUsar"], filme["citacao"], filme["parte"],
                 filme["cor"], filme["cartaz"], filme["id"]),
            )
            db.execute("DELETE FROM filme_temas WHERE filme_id = ?", (filme["id"],))
        for nome in dict.fromkeys(filme["temas"]):  # remove repetidos mantendo a ordem
            db.execute("INSERT OR IGNORE INTO temas (nome) VALUES (?)", (nome,))
            db.execute(
                """INSERT OR IGNORE INTO filme_temas (filme_id, tema_id)
                   SELECT ?, id FROM temas WHERE nome = ?""",
                (filme["id"], nome),
            )
        _limpar_temas_orfaos(db)


def excluir_filme(filme_id):
    """DELETE do filme; filme_temas e anotacoes saem juntos (ON DELETE CASCADE)."""
    db = get_db()
    with db:
        apagados = db.execute("DELETE FROM filmes WHERE id = ?", (filme_id,)).rowcount
        _limpar_temas_orfaos(db)
    return apagados > 0


def _limpar_temas_orfaos(db):
    db.execute("DELETE FROM temas WHERE id NOT IN (SELECT tema_id FROM filme_temas)")


def listar_anotacoes(filme_id=None):
    """Anotações com o título do filme (JOIN), da mais antiga para a mais recente."""
    sql = """
        SELECT a.id, a.filme_id, a.parte, a.texto, a.criado_em, f.titulo AS filme_titulo
        FROM anotacoes a
        JOIN filmes f ON f.id = a.filme_id
    """
    parametros = ()
    if filme_id:
        sql += " WHERE a.filme_id = ?"
        parametros = (filme_id,)
    sql += " ORDER BY a.rowid"
    return [dict(l) for l in get_db().execute(sql, parametros)]


def criar_anotacao(filme_id, parte, texto):
    existentes = {l["id"] for l in get_db().execute("SELECT id FROM anotacoes")}
    with get_db() as db:
        db.execute(
            "INSERT INTO anotacoes (id, filme_id, parte, texto, criado_em) VALUES (?,?,?,?,?)",
            (gerar_id(texto[:30], existentes), filme_id, parte, texto,
             datetime.now().strftime("%d/%m/%Y %H:%M")),
        )


def excluir_anotacao(anotacao_id):
    with get_db() as db:
        db.execute("DELETE FROM anotacoes WHERE id = ?", (anotacao_id,))


def contar(tabela):
    tabelas_validas = {"filmes", "temas", "anotacoes"}
    if tabela not in tabelas_validas:
        raise ValueError("Tabela inválida")
    return get_db().execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def gerar_id(texto, existentes):
    """Cria um identificador único em formato slug (ex.: 'cidade-de-deus')."""
    normalizado = unicodedata.normalize("NFKD", texto or "item")
    normalizado = normalizado.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", normalizado).strip("-") or "item"
    candidato, contador = slug, 2
    while candidato in existentes:
        candidato = f"{slug}-{contador}"
        contador += 1
    return candidato


# --------------------------------------------------------------------------
# Utilidades de apresentação
# --------------------------------------------------------------------------
def lojas(titulo):
    """Links de compra/aluguel do filme nas principais lojas digitais."""
    termo = quote_plus(titulo)
    return [
        {"nome": "Prime Video", "url": f"https://www.primevideo.com/search?phrase={termo}"},
        {"nome": "Apple TV", "url": f"https://tv.apple.com/search?term={termo}"},
        {"nome": "Google Play", "url": f"https://play.google.com/store/search?q={termo}&c=movies"},
    ]


def imdb_url(titulo, ano):
    return f"https://www.imdb.com/find/?q={quote_plus(f'{titulo} {ano}')}"


@app.context_processor
def injetar_globais():
    """Disponibiliza funções e dados para todos os templates."""
    return {
        "lojas": lojas,
        "imdb_url": imdb_url,
        "rotulo_parte": ROTULO_PARTE,
        "ano_atual": datetime.now().year,
    }


@app.template_filter("cartaz")
def filtro_cartaz(valor):
    """Aceita URL externa ou nome de arquivo local em /static/img."""
    if not valor:
        return ""
    if valor.startswith("http"):
        return valor
    return url_for("static", filename=f"img/{valor}")


# --------------------------------------------------------------------------
# Rota 1 — Página inicial (GET)
# --------------------------------------------------------------------------
@app.route("/")
def index():
    filmes = listar_filmes()
    destaques = sorted(filmes, key=lambda f: f.get("imdb") or 0, reverse=True)[:12]
    esteira_a = filmes[: len(filmes) // 2]
    esteira_b = filmes[len(filmes) // 2 :]
    return render_template(
        "index.html",
        titulo_pagina="Início",
        destaques=destaques,
        esteira_a=esteira_a,
        esteira_b=esteira_b,
        total=len(filmes),
        total_temas=len(temas_disponiveis()),
    )


# --------------------------------------------------------------------------
# Rota 2 — Catálogo de filmes com busca, filtro e ordenação (GET)
# --------------------------------------------------------------------------
@app.route("/filmes")
def filmes_lista():
    busca = (request.args.get("busca") or "").strip().lower()
    tema = request.args.get("tema") or ""
    parte = request.args.get("parte") or ""
    ordem = request.args.get("ordem") or "imdb"

    return render_template(
        "filmes.html",
        titulo_pagina="Filmes",
        filmes=consultar_filmes(busca, tema, parte, ordem),
        temas=temas_disponiveis(),
        busca=busca,
        tema=tema,
        parte=parte,
        ordem=ordem,
        partes=PARTES,
    )


# --------------------------------------------------------------------------
# Rota 3 — Detalhe do filme, com repertório e links de compra (GET)
# --------------------------------------------------------------------------
@app.route("/filmes/<filme_id>")
def filme_detalhe(filme_id):
    filme = buscar_filme(filme_id)
    if filme is None:
        return render_template("404.html", titulo_pagina="Não encontrado"), 404
    return render_template(
        "detalhe.html",
        titulo_pagina=filme["titulo"],
        filme=filme,
        relacionados=filmes_relacionados(filme_id),
        anotacoes=listar_anotacoes(filme_id),
    )


# --------------------------------------------------------------------------
# Rota 4 — Cadastrar novo filme (GET + POST) — CREATE
# --------------------------------------------------------------------------
@app.route("/filmes/novo", methods=["GET", "POST"])
def filme_novo():
    if request.method == "POST":
        erros = validar_filme(request.form)
        if erros:
            for erro in erros:
                flash(erro, "danger")
            return render_template(
                "form_filme.html",
                titulo_pagina="Novo filme",
                filme=request.form,
                partes=PARTES,
                modo="novo",
            )

        novo = montar_filme(request.form, gerar_id(request.form["titulo"], ids_de_filmes()))
        salvar_filme(novo, criar=True)
        flash(f"Filme “{novo['titulo']}” cadastrado com sucesso.", "success")
        return redirect(url_for("filme_detalhe", filme_id=novo["id"]))

    return render_template(
        "form_filme.html", titulo_pagina="Novo filme", filme={}, partes=PARTES, modo="novo"
    )


# --------------------------------------------------------------------------
# Rota 5 — Editar filme (GET + POST) — UPDATE
# --------------------------------------------------------------------------
@app.route("/filmes/<filme_id>/editar", methods=["GET", "POST"])
def filme_editar(filme_id):
    atual = buscar_filme(filme_id)
    if atual is None:
        return render_template("404.html", titulo_pagina="Não encontrado"), 404

    if request.method == "POST":
        erros = validar_filme(request.form)
        if erros:
            for erro in erros:
                flash(erro, "danger")
            return render_template(
                "form_filme.html",
                titulo_pagina="Editar filme",
                filme=request.form,
                partes=PARTES,
                modo="editar",
                filme_id=filme_id,
            )
        atualizado = montar_filme(request.form, filme_id)
        atualizado["cartaz"] = request.form.get("cartaz") or atual.get("cartaz", "")
        atualizado["cor"] = atual.get("cor", COR_PADRAO)
        salvar_filme(atualizado, criar=False)
        flash("Filme atualizado com sucesso.", "success")
        return redirect(url_for("filme_detalhe", filme_id=filme_id))

    filme = dict(atual)
    filme["temas_texto"] = ", ".join(filme.get("temas", []))
    return render_template(
        "form_filme.html",
        titulo_pagina="Editar filme",
        filme=filme,
        partes=PARTES,
        modo="editar",
        filme_id=filme_id,
    )


# --------------------------------------------------------------------------
# Rota 6 — Excluir filme (POST) — DELETE
# --------------------------------------------------------------------------
@app.route("/filmes/<filme_id>/excluir", methods=["POST"])
def filme_excluir(filme_id):
    if excluir_filme(filme_id):
        flash("Filme excluído do catálogo.", "success")
    else:
        flash("Filme não encontrado.", "danger")
    return redirect(url_for("filmes_lista"))


# --------------------------------------------------------------------------
# Rota 7 — Anotações de repertório: listar e criar (GET + POST)
# --------------------------------------------------------------------------
@app.route("/anotacoes", methods=["GET", "POST"])
def anotacoes():
    filmes = listar_filmes()
    if request.method == "POST":
        filme_id = request.form.get("filme_id", "")
        texto = (request.form.get("texto") or "").strip()
        parte = request.form.get("parte", "introducao")
        erros = []
        if not buscar_filme(filme_id):
            erros.append("Selecione um filme válido.")
        if len(texto) < 15:
            erros.append("A anotação deve ter pelo menos 15 caracteres.")
        if parte not in PARTES:
            erros.append("Selecione em qual parágrafo o repertório será usado.")
        if erros:
            for erro in erros:
                flash(erro, "danger")
        else:
            criar_anotacao(filme_id, parte, texto)
            flash("Anotação de repertório salva.", "success")
            return redirect(url_for("anotacoes"))

    titulos = {f["id"]: f["titulo"] for f in filmes}
    return render_template(
        "anotacoes.html",
        titulo_pagina="Minhas anotações",
        anotacoes=listar_anotacoes(),
        filmes=sorted(filmes, key=lambda f: f["titulo"].lower()),
        titulos=titulos,
        partes=PARTES,
    )


# --------------------------------------------------------------------------
# Rota 8 — Excluir anotação (POST)
# --------------------------------------------------------------------------
@app.route("/anotacoes/<anotacao_id>/excluir", methods=["POST"])
def anotacao_excluir(anotacao_id):
    excluir_anotacao(anotacao_id)
    flash("Anotação excluída.", "success")
    return redirect(url_for("anotacoes"))


# --------------------------------------------------------------------------
# Rota 9 — Estrutura da redação (GET)
# --------------------------------------------------------------------------
@app.route("/estrutura")
def estrutura():
    por_parte = {parte: consultar_filmes(parte=parte, ordem="imdb")[:4] for parte in PARTES}
    return render_template("estrutura.html", titulo_pagina="Estrutura da redação", por_parte=por_parte)


# --------------------------------------------------------------------------
# Rota 10 — Sobre o projeto (GET)
# --------------------------------------------------------------------------
@app.route("/sobre")
def sobre():
    return render_template(
        "sobre.html",
        titulo_pagina="Sobre",
        total=contar("filmes"),
        total_anotacoes=contar("anotacoes"),
    )


# --------------------------------------------------------------------------
# Rotas 11 e 12 — API simples em JSON (GET)
# --------------------------------------------------------------------------
@app.route("/api/filmes")
def api_filmes():
    """Lista filmes em JSON. Aceita ?busca=, ?tema=, ?parte= e ?ordem=."""
    filmes = consultar_filmes(
        (request.args.get("busca") or "").strip().lower(),
        request.args.get("tema") or "",
        request.args.get("parte") or "",
        request.args.get("ordem") or "imdb",
    )
    return jsonify({"total": len(filmes), "filmes": filmes})


@app.route("/api/filmes/<filme_id>")
def api_filme(filme_id):
    """Um filme em JSON, com temas e anotações."""
    filme = buscar_filme(filme_id)
    if filme is None:
        return jsonify({"erro": "Filme não encontrado"}), 404
    filme["anotacoes"] = listar_anotacoes(filme_id)
    return jsonify(filme)


# --------------------------------------------------------------------------
# Validação e montagem de dados
# --------------------------------------------------------------------------
def validar_filme(form):
    erros = []
    if len((form.get("titulo") or "").strip()) < 2:
        erros.append("Informe o título do filme.")
    if len((form.get("diretor") or "").strip()) < 2:
        erros.append("Informe o nome da direção.")
    try:
        ano = int(form.get("ano") or 0)
        if ano < 1895 or ano > datetime.now().year + 1:
            erros.append("Informe um ano de lançamento válido.")
    except ValueError:
        erros.append("O ano deve ser um número.")
    try:
        nota = float((form.get("imdb") or "0").replace(",", "."))
        if nota < 0 or nota > 10:
            erros.append("A nota do IMDb deve estar entre 0 e 10.")
    except ValueError:
        erros.append("A nota do IMDb deve ser um número.")
    if not (form.get("temas") or "").strip():
        erros.append("Informe pelo menos um tema.")
    if len((form.get("sinopse") or "").strip()) < 20:
        erros.append("A sinopse deve ter pelo menos 20 caracteres.")
    if len((form.get("citacao") or "").strip()) < 20:
        erros.append("Escreva a citação pronta para a redação (mínimo 20 caracteres).")
    if (form.get("parte") or "") not in PARTES:
        erros.append("Selecione o parágrafo em que o filme se encaixa.")
    return erros


def montar_filme(form, filme_id):
    return {
        "id": filme_id,
        "titulo": form["titulo"].strip(),
        "ano": int(form["ano"]),
        "diretor": form["diretor"].strip(),
        "imdb": round(float(form["imdb"].replace(",", ".")), 1),
        "temas": [t.strip() for t in form["temas"].split(",") if t.strip()],
        "sinopse": form["sinopse"].strip(),
        "comoUsar": (form.get("comoUsar") or "").strip(),
        "citacao": form["citacao"].strip(),
        "parte": form["parte"],
        "cor": COR_PADRAO,
        "cartaz": (form.get("cartaz") or "").strip(),
    }


@app.errorhandler(404)
def pagina_nao_encontrada(_erro):
    return render_template("404.html", titulo_pagina="Página não encontrada"), 404


# Garante as tabelas ao iniciar (inclusive sob o gunicorn, no Render).
iniciar_banco()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
