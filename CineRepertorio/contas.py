"""
CineRepertório — módulo de contas de usuário.

Responsável por cadastro, login, troca de conta e autenticação de dois
fatores (A2F) por código enviado ao e-mail. Os dados ficam na tabela
`usuarios` do banco SQLite, com a senha guardada apenas em formato de hash
PBKDF2-SHA256 + salt aleatório — a senha original nunca é gravada em disco.
"""



import hashlib
import random
import re
import secrets
import unicodedata
from datetime import datetime, timedelta

from banco import get_db

# Códigos de A2F pendentes ficam apenas em memória (expiram em 10 minutos).
CODIGOS_PENDENTES = {}
VALIDADE_CODIGO = timedelta(minutes=10)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


# --------------------------------------------------------------------------
# Persistência (SQLite)
# --------------------------------------------------------------------------
CAMPOS_EDITAVEIS = {"nome", "sobrenome", "salt", "senha_hash", "a2f", "iniciais"}


def _para_dict(linha):
    """Converte a linha do banco em dicionário (a2f vira booleano)."""
    if linha is None:
        return None
    usuario = dict(linha)
    usuario["a2f"] = bool(usuario["a2f"])
    return usuario


def ler_usuarios():
    linhas = get_db().execute("SELECT * FROM usuarios ORDER BY rowid").fetchall()
    return [_para_dict(l) for l in linhas]


def buscar_por_email(email):
    email = (email or "").strip().lower()
    linha = get_db().execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    return _para_dict(linha)


# --------------------------------------------------------------------------
# Segurança da senha
# --------------------------------------------------------------------------
def criar_hash(senha, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), 120000)
    return salt, digest.hex()


def senha_confere(usuario, senha):
    _, teste = criar_hash(senha, usuario["salt"])
    return secrets.compare_digest(teste, usuario["senha_hash"])


def forca_da_senha(senha):
    """Devolve uma lista de problemas encontrados na senha."""
    problemas = []
    if len(senha) < 8:
        problemas.append("A senha deve ter no mínimo 8 caracteres.")
    if not re.search(r"[A-Za-zÀ-ÿ]", senha):
        problemas.append("A senha deve conter pelo menos uma letra.")
    if not re.search(r"\d", senha):
        problemas.append("A senha deve conter pelo menos um número.")
    return problemas


# --------------------------------------------------------------------------
# Cadastro
# --------------------------------------------------------------------------
def iniciais(nome, sobrenome):
    texto = f"{nome} {sobrenome}".strip()
    partes = [p for p in texto.split() if p]
    letras = "".join(p[0] for p in partes[:2]).upper()
    normalizado = unicodedata.normalize("NFKD", letras)
    return normalizado.encode("ascii", "ignore").decode("ascii") or "?"


def validar_cadastro(form):
    erros = []
    nome = (form.get("nome") or "").strip()
    sobrenome = (form.get("sobrenome") or "").strip()
    email = (form.get("email") or "").strip().lower()
    senha = form.get("senha") or ""
    confirmar = form.get("confirmar") or ""

    if len(nome) < 2:
        erros.append("Informe o seu nome.")
    if len(sobrenome) < 2:
        erros.append("Informe o seu sobrenome.")
    if not EMAIL_REGEX.match(email):
        erros.append("Informe um e-mail válido.")
    elif buscar_por_email(email):
        erros.append("Já existe uma conta cadastrada com este e-mail.")
    erros.extend(forca_da_senha(senha))
    if senha != confirmar:
        erros.append("As duas senhas digitadas não são iguais.")
    if (form.get("protecao") or "") not in ("a2f", "simples"):
        erros.append("Escolha o nível de proteção da conta.")
    return erros


def criar_usuario(form):
    """INSERT na tabela usuarios e devolve o registro criado."""
    salt, senha_hash = criar_hash(form["senha"])
    usuario = {
        "id": secrets.token_hex(8),
        "nome": form["nome"].strip(),
        "sobrenome": form["sobrenome"].strip(),
        "email": form["email"].strip().lower(),
        "salt": salt,
        "senha_hash": senha_hash,
        "a2f": form.get("protecao") == "a2f",
        "iniciais": iniciais(form["nome"], form["sobrenome"]),
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    db = get_db()
    with db:
        db.execute(
            """INSERT INTO usuarios
               (id, nome, sobrenome, email, salt, senha_hash, a2f, iniciais, criado_em)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (usuario["id"], usuario["nome"], usuario["sobrenome"], usuario["email"],
             usuario["salt"], usuario["senha_hash"], int(usuario["a2f"]),
             usuario["iniciais"], usuario["criado_em"]),
        )
    return usuario


def atualizar_usuario(usuario_id, campos):
    """UPDATE de campos permitidos do usuário; devolve o registro atualizado."""
    campos = {k: v for k, v in campos.items() if k in CAMPOS_EDITAVEIS}
    if not campos:
        return None
    if "a2f" in campos:
        campos["a2f"] = int(bool(campos["a2f"]))
    db = get_db()
    with db:
        atribuicoes = ", ".join(f"{coluna} = ?" for coluna in campos)
        db.execute(
            f"UPDATE usuarios SET {atribuicoes} WHERE id = ?",
            (*campos.values(), usuario_id),
        )
    linha = db.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return _para_dict(linha)


# --------------------------------------------------------------------------
# Autenticação de dois fatores (A2F)
# --------------------------------------------------------------------------
def gerar_codigo(email):
    """Gera o código de 6 dígitos e simula o envio por e-mail.

    Em produção, este ponto chamaria um serviço de SMTP. No projeto
    acadêmico o código é escrito no terminal e devolvido para a interface,
    para que a verificação possa ser testada sem servidor de e-mail.
    """
    codigo = f"{random.randint(0, 999999):06d}"
    CODIGOS_PENDENTES[email] = {"codigo": codigo, "expira": datetime.now() + VALIDADE_CODIGO}
    print(f"[A2F] Código enviado para {email}: {codigo}")
    return codigo


def validar_codigo(email, informado):
    registro = CODIGOS_PENDENTES.get(email)
    if not registro:
        return False, "Nenhum código pendente. Faça login novamente."
    if datetime.now() > registro["expira"]:
        CODIGOS_PENDENTES.pop(email, None)
        return False, "O código expirou. Solicite um novo."
    if (informado or "").strip() != registro["codigo"]:
        return False, "Código incorreto. Confira o e-mail e tente de novo."
    CODIGOS_PENDENTES.pop(email, None)
    return True, ""


def dados_publicos(usuario):
    """Versão do usuário que pode ir para a sessão/template (sem senha)."""
    return {
        "id": usuario["id"],
        "nome": usuario["nome"],
        "sobrenome": usuario["sobrenome"],
        "email": usuario["email"],
        "iniciais": usuario["iniciais"],
        "a2f": usuario["a2f"],
    }
