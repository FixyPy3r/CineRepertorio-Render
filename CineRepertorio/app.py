"""
CineRepertório — UC35: Projeto Integrador Back-end
Aplicação web de repertórios socioculturais (filmes) para a redação do ENEM.

Armazenamento: banco relacional SQLite (banco.db) com as tabelas
filmes, temas, filme_temas, usuarios e anotacoes, ligadas por chaves estrangeiras.
Módulos: banco.py (conexão), contas.py (login, cadastro e A2F) e
ia.py (conversa geral do Briggs e apoio à redação).
CRUD completo: anotações de repertório do usuário (criar, ler, editar, excluir).
O catálogo de filmes é somente leitura e se renova sozinho a cada dia
(seleção rotativa por data), sem edição manual.
Consultas com JOIN: catálogo, filmes relacionados e anotações.
API em JSON: /api/filmes, /api/filmes/<id> e /api/assistente.
"""



import os
import random
import smtplib
import ssl
from email.message import EmailMessage
import re
import unicodedata
from datetime import date, datetime
from functools import wraps
from urllib.parse import quote_plus
import secrets
import time


def carregar_arquivo_env(caminho=None):
    """Carrega variáveis de um .env local sem sobrescrever o ambiente do sistema."""
    caminho = caminho or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(caminho):
        return
    try:
        with open(caminho, encoding="utf-8") as arquivo_env:
            for linha in arquivo_env:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                chave, valor = linha.split("=", 1)
                chave = chave.strip()
                valor = valor.strip().strip('"').strip("'")
                if chave and chave.replace("_", "").isalnum():
                    os.environ.setdefault(chave, valor)
    except OSError as erro:
        raise RuntimeError(f"Não foi possível ler o arquivo .env: {erro}") from erro


carregar_arquivo_env()

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import banco
import contas
import ia
from banco import contar, get_db

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
app.secret_key = os.environ.get("CINE_SECRET") or secrets.token_hex(32)
app.teardown_appcontext(banco.fechar_db)

PARTES = ["introducao", "desenvolvimento", "conclusao"]
ROTULO_PARTE = {
    "introducao": "Introdução",
    "desenvolvimento": "Desenvolvimento",
    "conclusao": "Conclusão",
}
COR_PADRAO = "from-amber-500/30 to-slate-900/60"


# --------------------------------------------------------------------------
# Camada de persistência (SQLite) — filmes
# --------------------------------------------------------------------------
def _filme_para_dict(linha, temas):
    """Converte uma linha do banco no dicionário usado pelos templates e pela IA."""
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


def consultar_filmes(busca="", tema="", parte="", ordem="original"):
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
        # f.rowid desempata mantendo a ordem de cadastro do catálogo
        "ano": "f.ano DESC, f.rowid",
        "titulo": "minusc(f.titulo), f.rowid",
        "imdb": "f.imdb DESC, f.rowid",
        "original": "f.rowid",  # ordem de cadastro do catálogo
    }
    sql = "SELECT f.* FROM filmes f"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)
    sql += " ORDER BY " + ordenacoes.get(ordem, ordenacoes["imdb"])

    linhas = get_db().execute(sql, parametros).fetchall()
    temas = _temas_por_filme()
    return [_filme_para_dict(l, temas.get(l["id"], [])) for l in linhas]


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
    return _filme_para_dict(linha, temas)


def filmes_relacionados(filme_id, limite=6):
    """Filmes que compartilham temas com o filme informado (JOIN + GROUP BY)."""
    linhas = get_db().execute(
        """
        SELECT f.*
        FROM filmes f
        JOIN filme_temas ft ON ft.filme_id = f.id
        WHERE f.id <> :id
          AND ft.tema_id IN (SELECT tema_id FROM filme_temas WHERE filme_id = :id)
        GROUP BY f.id
        ORDER BY COUNT(*) DESC, f.imdb DESC
        LIMIT :limite
        """,
        {"id": filme_id, "limite": limite},
    ).fetchall()
    temas = _temas_por_filme()
    return [_filme_para_dict(l, temas.get(l["id"], [])) for l in linhas]


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


# --------------------------------------------------------------------------
# Camada de persistência (SQLite) — anotações do usuário (CRUD)
# --------------------------------------------------------------------------
def listar_anotacoes(usuario_id=None, filme_id=None):
    """Anotações com o título do filme (JOIN), da mais antiga para a mais recente."""
    sql = """
        SELECT a.id, a.usuario_id, a.filme_id, a.parte, a.texto, a.criado_em,
               f.titulo AS filme_titulo
        FROM anotacoes a
        JOIN filmes f ON f.id = a.filme_id
    """
    condicoes, parametros = [], []
    if usuario_id:
        condicoes.append("a.usuario_id = ?")
        parametros.append(usuario_id)
    if filme_id:
        condicoes.append("a.filme_id = ?")
        parametros.append(filme_id)
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)
    sql += " ORDER BY a.rowid"
    return [dict(l) for l in get_db().execute(sql, parametros)]


def anotacoes_do_usuario():
    usuario = session.get("usuario")
    if not usuario:
        return []
    return listar_anotacoes(usuario_id=usuario["id"])


def criar_anotacao(usuario_id, filme_id, parte, texto):
    """INSERT de uma anotação do usuário."""
    existentes = {l["id"] for l in get_db().execute("SELECT id FROM anotacoes")}
    with get_db() as db:
        db.execute(
            """INSERT INTO anotacoes (id, usuario_id, filme_id, parte, texto, criado_em)
               VALUES (?,?,?,?,?,?)""",
            (gerar_id(texto[:30], existentes), usuario_id, filme_id, parte, texto,
             datetime.now().strftime("%d/%m/%Y %H:%M")),
        )


def atualizar_anotacao(anotacao_id, usuario_id, texto, parte):
    """UPDATE da anotação (só se ela pertencer ao usuário). Devolve True se alterou."""
    atual = get_db().execute(
        "SELECT parte FROM anotacoes WHERE id = ? AND usuario_id = ?",
        (anotacao_id, usuario_id),
    ).fetchone()
    if atual is None:
        return False
    nova_parte = parte if parte in PARTES else atual["parte"]
    with get_db() as db:
        db.execute(
            "UPDATE anotacoes SET texto = ?, parte = ?, criado_em = ? WHERE id = ? AND usuario_id = ?",
            (texto, nova_parte, datetime.now().strftime("%d/%m/%Y %H:%M"), anotacao_id, usuario_id),
        )
    return True


def excluir_anotacao(anotacao_id, usuario_id):
    """DELETE da anotação (só se ela pertencer ao usuário)."""
    with get_db() as db:
        db.execute(
            "DELETE FROM anotacoes WHERE id = ? AND usuario_id = ?",
            (anotacao_id, usuario_id),
        )


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


def selecao_do_dia(filmes, quantidade=12):
    """Catálogo que se renova sozinho: a vitrine muda a cada dia.

    Usa a data como semente do sorteio, então todos os visitantes veem a
    mesma seleção no mesmo dia e uma seleção diferente no dia seguinte —
    sem ninguém precisar editar o catálogo.
    """
    if not filmes:
        return []
    sorteio = random.Random(date.today().toordinal())
    copia = list(filmes)
    sorteio.shuffle(copia)
    return copia[:quantidade]


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
        "usuario": session.get("usuario"),
        "perguntas_ia": ia.PERGUNTAS_SUGERIDAS[:4],
        "briggs_api_ativa": ia.api_ativa(),
        "atualizado_em": date.today().strftime("%d/%m/%Y"),
    }


@app.template_filter("cartaz")
def filtro_cartaz(valor):
    """Aceita URL externa ou nome de arquivo local em /static/img."""
    if not valor:
        return ""
    if valor.startswith("http"):
        return valor
    return url_for("static", filename=f"img/{valor}")


def login_obrigatorio(view):
    """Protege as rotas que dependem de uma conta ativa."""

    @wraps(view)
    def envolvida(*args, **kwargs):
        if not session.get("usuario"):
            flash("Entre na sua conta para acessar esta página.", "danger")
            return redirect(url_for("entrar", proxima=request.path))
        return view(*args, **kwargs)

    return envolvida


# --------------------------------------------------------------------------
# Rota 1 — Página inicial (GET)
# --------------------------------------------------------------------------
@app.route("/")
def index():
    filmes = listar_filmes()
    # Vitrine da home: só filmes que já têm cartaz (os demais aparecem no catálogo).
    vitrine = [f for f in filmes if f["cartaz"]] or filmes
    destaques = selecao_do_dia(vitrine, 10)
    esteira_a = vitrine[: len(vitrine) // 2]
    esteira_b = vitrine[len(vitrine) // 2 :]
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
    anotacoes = [a for a in anotacoes_do_usuario() if a["filme_id"] == filme_id]
    return render_template(
        "detalhe.html",
        titulo_pagina=filme["titulo"],
        filme=filme,
        relacionados=filmes_relacionados(filme_id),
        anotacoes=anotacoes,
    )


# --------------------------------------------------------------------------
# Rota 4 — Criar conta (GET + POST) — CREATE de usuário
# --------------------------------------------------------------------------
@app.route("/conta/criar", methods=["GET", "POST"])
def criar_conta():
    if request.method == "POST":
        erros = contas.validar_cadastro(request.form)
        if erros:
            for erro in erros:
                flash(erro, "danger")
            return render_template(
                "criar_conta.html", titulo_pagina="Criar conta", form=request.form
            )
        usuario = contas.criar_usuario(request.form)
        if usuario["a2f"]:
            codigo = contas.gerar_codigo(usuario["email"])
            session["a2f_email"] = usuario["email"]
            session["a2f_proxima"] = url_for("index")
            flash("Conta criada. Enviamos um código de verificação para o seu e-mail.", "success")
            return render_template(
                "verificar.html",
                titulo_pagina="Verificação em duas etapas",
                email=usuario["email"],
                codigo_demo=codigo,
            )
        session["usuario"] = contas.dados_publicos(usuario)
        flash(f"Bem-vindo(a), {usuario['nome']}! Conta criada com sucesso.", "success")
        return redirect(url_for("index"))

    return render_template("criar_conta.html", titulo_pagina="Criar conta", form={})


# --------------------------------------------------------------------------
# Rota 5 — Entrar / trocar de conta (GET + POST)
# --------------------------------------------------------------------------
@app.route("/conta/entrar", methods=["GET", "POST"])
def entrar():
    proxima = request.values.get("proxima") or url_for("index")
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""
        usuario = contas.buscar_por_email(email)
        if not usuario or not contas.senha_confere(usuario, senha):
            flash("E-mail ou senha incorretos.", "danger")
            return render_template("entrar.html", titulo_pagina="Entrar", email=email, proxima=proxima)

        if usuario["a2f"]:
            codigo = contas.gerar_codigo(usuario["email"])
            session["a2f_email"] = usuario["email"]
            session["a2f_proxima"] = proxima
            return render_template(
                "verificar.html",
                titulo_pagina="Verificação em duas etapas",
                email=usuario["email"],
                codigo_demo=codigo,
            )

        session["usuario"] = contas.dados_publicos(usuario)
        flash(f"Olá de novo, {usuario['nome']}!", "success")
        return redirect(proxima)

    return render_template("entrar.html", titulo_pagina="Entrar", email="", proxima=proxima)


# --------------------------------------------------------------------------
# Rota 6 — Verificar código de dois fatores (POST) e sair (GET)
# --------------------------------------------------------------------------
@app.route("/conta/verificar", methods=["POST"])
def verificar_codigo():
    email = session.get("a2f_email")
    if not email:
        flash("Sessão de verificação expirada. Entre novamente.", "danger")
        return redirect(url_for("entrar"))

    ok, mensagem = contas.validar_codigo(email, request.form.get("codigo"))
    if not ok:
        flash(mensagem, "danger")
        return render_template(
            "verificar.html", titulo_pagina="Verificação em duas etapas", email=email, codigo_demo=""
        )

    usuario = contas.buscar_por_email(email)
    session["usuario"] = contas.dados_publicos(usuario)
    proxima = session.pop("a2f_proxima", url_for("index"))
    session.pop("a2f_email", None)
    flash("Verificação concluída. Sua conta está protegida com dois fatores.", "success")
    return redirect(proxima)


@app.route("/conta/sair")
def sair():
    session.pop("usuario", None)
    flash("Você saiu da conta.", "success")
    return redirect(url_for("index"))


# --------------------------------------------------------------------------
# Rota 7 — Anotações de repertório: listar e criar (GET + POST)
# --------------------------------------------------------------------------
@app.route("/anotacoes", methods=["GET", "POST"])
@login_obrigatorio
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
            criar_anotacao(session["usuario"]["id"], filme_id, parte, texto)
            flash("Anotação de repertório salva.", "success")
            return redirect(url_for("anotacoes"))

    return render_template(
        "anotacoes.html",
        titulo_pagina="Minhas anotações",
        anotacoes=anotacoes_do_usuario(),
        filmes=sorted(filmes, key=lambda f: f["titulo"].lower()),
        titulos={f["id"]: f["titulo"] for f in filmes},
        partes=PARTES,
    )


# --------------------------------------------------------------------------
# Rota 8 — Editar anotação (POST) — UPDATE
# --------------------------------------------------------------------------
@app.route("/anotacoes/<anotacao_id>/editar", methods=["POST"])
@login_obrigatorio
def anotacao_editar(anotacao_id):
    texto = (request.form.get("texto") or "").strip()
    parte = request.form.get("parte", "introducao")
    if len(texto) < 15:
        flash("A anotação deve ter pelo menos 15 caracteres.", "danger")
    elif atualizar_anotacao(anotacao_id, session["usuario"]["id"], texto, parte):
        flash("Anotação atualizada.", "success")
    else:
        flash("Anotação não encontrada.", "danger")
    return redirect(url_for("anotacoes"))


# --------------------------------------------------------------------------
# Rota 9 — Excluir anotação (POST) — DELETE
# --------------------------------------------------------------------------
@app.route("/anotacoes/<anotacao_id>/excluir", methods=["POST"])
@login_obrigatorio
def anotacao_excluir(anotacao_id):
    excluir_anotacao(anotacao_id, session["usuario"]["id"])
    flash("Anotação excluída.", "success")
    return redirect(url_for("anotacoes"))


# --------------------------------------------------------------------------
# Contato e notificações por e-mail
# --------------------------------------------------------------------------
EMAIL_DESTINO_CONTATO = "cinerepertorio@gmail.com"


def enviar_email_contato(nome, email_resposta, assunto, mensagem):
    """Envia uma mensagem de contato usando SMTP configurado no ambiente.

    Para Gmail: smtp.gmail.com + porta 587 (STARTTLS) ou 465 (SSL).
    SMTP_PASSWORD deve ser uma senha de app do provedor, nunca a senha
    normal da conta. As credenciais ficam fora do código-fonte.
    """
    host = (os.environ.get("SMTP_HOST") or "").strip()
    usuario_smtp = (os.environ.get("SMTP_USER") or "").strip()
    senha_smtp = (os.environ.get("SMTP_PASSWORD") or "").strip()
    remetente = (os.environ.get("SMTP_FROM") or usuario_smtp).strip()
    if not all([host, usuario_smtp, senha_smtp, remetente]):
        raise RuntimeError("Configuração SMTP incompleta.")

    porta = int(os.environ.get("SMTP_PORT", "587"))
    timeout = int(os.environ.get("SMTP_TIMEOUT", "20"))
    usa_ssl = os.environ.get("SMTP_USE_SSL", "").strip().lower() in {"1", "true", "yes", "sim"} or porta == 465

    # Evita caracteres de quebra de linha nos cabeçalhos do e-mail.
    assunto_seguro = " ".join(assunto.replace("\r", " ").replace("\n", " ").split())
    nome_seguro = " ".join(nome.replace("\r", " ").replace("\n", " ").split())

    email_msg = EmailMessage()
    email_msg["Subject"] = f"CineRepertório | {assunto_seguro}"
    email_msg["From"] = remetente
    email_msg["To"] = EMAIL_DESTINO_CONTATO
    email_msg["Reply-To"] = email_resposta
    email_msg.set_content(
        "Mensagem enviada pelo CineRepertório\n\n"
        f"Nome: {nome_seguro}\n"
        f"E-mail para resposta: {email_resposta}\n"
        f"Assunto: {assunto_seguro}\n\n"
        f"{mensagem}"
    )

    contexto_tls = ssl.create_default_context()
    if usa_ssl:
        with smtplib.SMTP_SSL(host, porta, timeout=timeout, context=contexto_tls) as servidor:
            servidor.login(usuario_smtp, senha_smtp)
            servidor.send_message(email_msg)
    else:
        with smtplib.SMTP(host, porta, timeout=timeout) as servidor:
            servidor.ehlo()
            servidor.starttls(context=contexto_tls)
            servidor.ehlo()
            servidor.login(usuario_smtp, senha_smtp)
            servidor.send_message(email_msg)


@app.route("/notificacoes", methods=["GET", "POST"])
def notificacoes():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()[:100]
        email = (request.form.get("email") or "").strip()[:160]
        assunto = (request.form.get("assunto") or "").strip()[:140]
        mensagem = (request.form.get("mensagem") or "").strip()[:4000]
        # Campo-armadilha simples para reduzir envios automatizados.
        if request.form.get("website"):
            flash("Não foi possível enviar a mensagem.", "danger")
            return redirect(url_for("notificacoes"))
        if (not nome or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
                or not assunto or len(mensagem) < 10):
            flash("Confira os campos. A mensagem precisa ter pelo menos 10 caracteres.", "danger")
            return redirect(url_for("notificacoes"))
        if not all((os.environ.get("SMTP_HOST"), os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD"))):
            flash("O formulário está pronto, mas o envio ainda precisa ser ativado pelo administrador com as configurações SMTP do projeto.", "warning")
            return redirect(url_for("notificacoes"))
        try:
            enviar_email_contato(nome, email, assunto, mensagem)
            flash("Mensagem enviada! A equipe do CineRepertório recebeu seu contato.", "success")
        except (OSError, ValueError, RuntimeError, smtplib.SMTPException):
            app.logger.exception("Falha ao enviar mensagem de contato")
            flash("Não foi possível enviar agora. Confira a configuração SMTP ou tente novamente mais tarde.", "danger")
        return redirect(url_for("notificacoes"))
    return render_template("notificacoes.html", titulo_pagina="Notificações")


# --------------------------------------------------------------------------
# Rota 10 — Assistente de redação (IA) — página e API (GET + POST)
# --------------------------------------------------------------------------
@app.route("/assistente")
def assistente():
    return render_template(
        "assistente.html",
        titulo_pagina="Converse com Briggs",
        sugestoes=ia.PERGUNTAS_SUGERIDAS,
    )


_briggs_requisicoes = {}


@app.route("/api/assistente", methods=["POST"])
def api_assistente():
    """Chat geral do Briggs com histórico limitado e controle básico de frequência."""
    agora = time.monotonic()
    ip = request.remote_addr or "desconhecido"
    recentes = [t for t in _briggs_requisicoes.get(ip, []) if agora - t < 60]
    if len(recentes) >= 18:
        return jsonify({"texto": "Você enviou muitas mensagens em pouco tempo. Aguarde um minuto e tente novamente."}), 429
    recentes.append(agora)
    _briggs_requisicoes[ip] = recentes

    dados = request.get_json(silent=True) or {}
    mensagem = dados.get("mensagem", "")
    if not isinstance(mensagem, str) or not mensagem.strip():
        return jsonify({"texto": "Escreva uma mensagem para o Briggs."}), 400
    if len(mensagem) > 5000:
        return jsonify({"texto": "A mensagem ultrapassou o limite de 5.000 caracteres. Envie em partes menores."}), 400
    historico = dados.get("historico", [])
    if not isinstance(historico, list):
        historico = []
    resposta = ia.conversar(mensagem, historico, listar_filmes())
    codigo = 200 if resposta.get("modo") != "erro" else 502
    return jsonify(resposta), codigo


# --------------------------------------------------------------------------
# Rotas 11 e 12 — API simples em JSON do catálogo (GET)
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
    """Um filme em JSON, com seus temas."""
    filme = buscar_filme(filme_id)
    if filme is None:
        return jsonify({"erro": "Filme não encontrado"}), 404
    return jsonify(filme)


# --------------------------------------------------------------------------
# Rota 13 — Estrutura da redação (GET)
# --------------------------------------------------------------------------
@app.route("/estrutura")
def estrutura():
    por_parte = {parte: consultar_filmes(parte=parte, ordem="imdb")[:4] for parte in PARTES}
    return render_template("estrutura.html", titulo_pagina="Estrutura da redação", por_parte=por_parte)




# --------------------------------------------------------------------------
# Rota 14 — Acessibilidade (GET)
# --------------------------------------------------------------------------
@app.route("/acessibilidade")
def acessibilidade():
    return render_template("acessibilidade.html", titulo_pagina="Acessibilidade")


# --------------------------------------------------------------------------
# Rota 15 — Sobre o projeto (GET)
# --------------------------------------------------------------------------
@app.route("/sobre")
def sobre():
    return render_template(
        "sobre.html",
        titulo_pagina="Sobre",
        total=contar("filmes"),
        total_anotacoes=contar("anotacoes"),
        total_usuarios=contar("usuarios"),
    )


@app.errorhandler(404)
def pagina_nao_encontrada(_erro):
    return render_template("404.html", titulo_pagina="Página não encontrada"), 404


# Garante as tabelas ao iniciar (inclusive sob o gunicorn, no Render).
banco.iniciar_banco()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
