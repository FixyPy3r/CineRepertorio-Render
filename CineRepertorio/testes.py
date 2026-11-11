"""
Testes automatizados do CineRepertório. Execute: python testes.py

Durante os testes é usada uma cópia temporária do banco de dados, para não alterar o original.
"""



import os
import shutil
import sqlite3
import sys
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp()
COPIA = os.path.join(TMP, "banco_teste.db")
shutil.copy(os.path.join(BASE, "banco.db"), COPIA)
os.environ["DATABASE"] = COPIA  # o app usa a cópia

sys.path.insert(0, BASE)
import app as aplicacao  # noqa: E402
import contas  # noqa: E402

cliente = aplicacao.app.test_client()
falhas = 0


def consultar(sql, params=()):
    con = sqlite3.connect(COPIA)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def checar(descricao, condicao):
    global falhas
    print(("  OK  " if condicao else " FALHA ") + descricao)
    if not condicao:
        falhas += 1


print("== ARMAZENAMENTO ==")
checar("projeto não usa mais arquivos JSON de dados", not os.path.exists(os.path.join(BASE, "data")))
checar("banco tem 112 filmes", consultar("SELECT COUNT(*) FROM filmes")[0][0] == 112)
checar("todo filme tem 2 a 3 temas", consultar("SELECT COUNT(*) FROM filmes f WHERE (SELECT COUNT(*) FROM filme_temas t WHERE t.filme_id=f.id) < 2")[0][0] == 0)
checar("todo filme do catálogo tem cartaz", consultar("SELECT COUNT(*) FROM filmes WHERE cartaz IS NULL OR cartaz=''")[0][0] == 0)
checar("chaves estrangeiras íntegras", consultar("PRAGMA foreign_key_check") == [])

print("\n== ROTAS PÚBLICAS ==")
for rota in ["/", "/filmes", "/filmes/ainda-estou-aqui", "/filmes/zootopia", "/filmes/marte-um", "/filmes?tema=Educa%C3%A7%C3%A3o&ordem=ano", "/filmes?busca=EDUCA%C3%87%C3%83O",
             "/filmes/parasita", "/estrutura", "/assistente", "/acessibilidade", "/sobre",
             "/conta/criar", "/conta/entrar", "/notificacoes"]:
    checar(f"GET {rota} -> 200", cliente.get(rota).status_code == 200)
checar("GET /filmes/inexistente -> 404", cliente.get("/filmes/inexistente").status_code == 404)

print("\n== API JSON ==")
r = cliente.get("/api/filmes")
dados = r.get_json()
checar("GET /api/filmes devolve JSON com 112 filmes", r.is_json and dados["total"] == 112)
checar("cada filme traz a lista de temas", all(f["temas"] for f in dados["filmes"]))
checar("filtro ?tema= na API", all("Educação" in f["temas"]
       for f in cliente.get("/api/filmes?tema=Educa%C3%A7%C3%A3o").get_json()["filmes"]))
checar("GET /api/filmes/parasita", cliente.get("/api/filmes/parasita").get_json()["titulo"] == "Parasita")
checar("GET /api/filmes/xxx -> 404 em JSON", cliente.get("/api/filmes/xxx").status_code == 404)

print("\n== PROTEÇÃO DE ROTA ==")
checar("/anotacoes exige login", cliente.get("/anotacoes").status_code == 302)

print("\n== CONTA SEM A2F ==")
resposta = cliente.post("/conta/criar", data=dict(
    nome="Teste", sobrenome="UC35", email="teste.uc35@exemplo.com",
    senha="senha1234", confirmar="senha1234", protecao="simples"), follow_redirects=True)
checar("cadastro simples cria sessão", resposta.status_code == 200)
linha = consultar("SELECT senha_hash, salt, a2f FROM usuarios WHERE email='teste.uc35@exemplo.com'")
checar("usuário gravado na tabela usuarios", len(linha) == 1 and linha[0][2] == 0)
checar("senha guardada só como hash (nunca em texto)", linha and "senha1234" not in linha[0][0] and len(linha[0][0]) == 64)
checar("e-mail repetido é rejeitado", "Já existe uma conta" in cliente.post("/conta/criar", data=dict(
    nome="Outro", sobrenome="Nome", email="teste.uc35@exemplo.com", senha="senha1234",
    confirmar="senha1234", protecao="simples")).get_data(as_text=True))
checar("/anotacoes acessível logado", cliente.get("/anotacoes").status_code == 200)

print("\n== CRUD DE ANOTAÇÕES ==")
cliente.post("/anotacoes", data=dict(filme_id="parasita", parte="introducao",
             texto="Usar Parasita para mostrar a desigualdade espacial."), follow_redirects=True)
criada = consultar("SELECT id, usuario_id FROM anotacoes WHERE texto LIKE '%desigualdade espacial%'")
checar("CREATE grava no banco com o usuario_id", len(criada) == 1 and criada[0][1])
if criada:
    anot_id = criada[0][0]
    checar("anotação aparece na página do filme", "desigualdade espacial" in cliente.get("/filmes/parasita").get_data(as_text=True))
    cliente.post(f"/anotacoes/{anot_id}/editar",
                 data=dict(texto="Texto atualizado pelo teste automatizado.", parte="conclusao"),
                 follow_redirects=True)
    checar("UPDATE altera texto e parágrafo", consultar(
        "SELECT texto, parte FROM anotacoes WHERE id=?", (anot_id,))[0] == ("Texto atualizado pelo teste automatizado.", "conclusao"))

    print("\n== ISOLAMENTO ENTRE USUÁRIOS ==")
    outro = aplicacao.app.test_client()
    outro.post("/conta/criar", data=dict(nome="Segundo", sobrenome="Usuario", email="segundo.uc35@exemplo.com",
               senha="senha1234", confirmar="senha1234", protecao="simples"))
    checar("outro usuário não vê a anotação", "Texto atualizado" not in outro.get("/anotacoes").get_data(as_text=True))
    outro.post(f"/anotacoes/{anot_id}/excluir", follow_redirects=True)
    checar("outro usuário não consegue excluir", consultar("SELECT COUNT(*) FROM anotacoes WHERE id=?", (anot_id,))[0][0] == 1)
    outro.post(f"/anotacoes/{anot_id}/editar", data=dict(texto="Tentativa de invasão da anotação alheia.", parte="introducao"))
    checar("outro usuário não consegue editar", consultar("SELECT texto FROM anotacoes WHERE id=?", (anot_id,))[0][0].startswith("Texto atualizado"))

    cliente.post(f"/anotacoes/{anot_id}/excluir", follow_redirects=True)
    checar("DELETE remove do banco", consultar("SELECT COUNT(*) FROM anotacoes WHERE id=?", (anot_id,))[0][0] == 0)
cliente.post("/anotacoes", data=dict(filme_id="x", parte="introducao", texto="curta"))
checar("anotação inválida é rejeitada", consultar("SELECT COUNT(*) FROM anotacoes")[0][0] == 0)

print("\n== ASSISTENTE DE IA ==")
dados = cliente.post("/api/assistente", json={"mensagem": "Escreva uma redação completa sobre saúde mental"}).get_json()
checar("gera redação estruturada", any("Introdução" in b["titulo"] for b in dados["blocos"]) and len(dados["blocos"]) >= 5)
checar("inclui projeto de texto antes dos parágrafos", dados["blocos"][0]["tipo"] == "plano")
checar("resposta identifica o parceiro masculino de cinema", dados.get("persona", {}).get("nome") == "Briggs")
checar("personalidade do Briggs está definida", "cavalheiro cinéfilo" in dados.get("persona", {}).get("descricao", ""))
checar("sugere videoaulas", len(dados["videos"]) == 2)
checar("sugere novas perguntas", len(dados["sugestoes"]) > 0)
correcao = cliente.post("/api/assistente", json={"mensagem": "Corrija a minha redação. " + ("A desigualdade social persiste no Brasil e afeta a educação pública. " * 15)}).get_json()
checar("corrige texto colado com ressalva de estimativa", "orientativa" in correcao["texto"])

print("\n== CONTA COM A2F ==")
a2f = aplicacao.app.test_client()
a2f.post("/conta/criar", data=dict(nome="Dois", sobrenome="Fatores", email="a2f.uc35@exemplo.com",
         senha="senha1234", confirmar="senha1234", protecao="a2f"))
codigo = contas.CODIGOS_PENDENTES["a2f.uc35@exemplo.com"]["codigo"]
checar("código de 6 dígitos gerado", len(codigo) == 6)
checar("usuário A2F gravado com a2f=1", consultar("SELECT a2f FROM usuarios WHERE email='a2f.uc35@exemplo.com'")[0][0] == 1)
checar("sem verificar, /anotacoes continua bloqueada", a2f.get("/anotacoes").status_code == 302)
checar("código errado é rejeitado", "incorreto" in a2f.post("/conta/verificar", data={"codigo": "000000"}).get_data(as_text=True))
checar("código correto libera acesso", a2f.post("/conta/verificar", data={"codigo": codigo}, follow_redirects=True).status_code == 200)
checar("anotações liberadas após A2F", a2f.get("/anotacoes").status_code == 200)

print("\n== LOGIN POR E-MAIL E SENHA (lendo do banco) ==")
novo = aplicacao.app.test_client()
checar("senha errada é recusada", "incorretos" in novo.post("/conta/entrar", data=dict(email="teste.uc35@exemplo.com", senha="errada123")).get_data(as_text=True))
checar("senha certa entra", novo.post("/conta/entrar", data=dict(email="teste.uc35@exemplo.com", senha="senha1234")).status_code == 302)

print("\n== JOIN E PÁGINAS ==")
checar("sobre conta usuários pelo banco", "Hoje o catálogo tem" in cliente.get("/sobre").get_data(as_text=True))
with aplicacao.app.app_context():
    rel = aplicacao.filmes_relacionados("parasita")
    checar("filmes relacionados vêm do banco (JOIN)", 0 < len(rel) <= 6 and all(f["id"] != "parasita" for f in rel))
    checar("catálogo mantém a ordem original", aplicacao.listar_filmes()[0]["id"] == "que-horas-ela-volta")

print("\n== HERANÇA, FAVICON E ACESSIBILIDADE ==")
html = cliente.get("/filmes").get_data(as_text=True)
checar("base.html aplicado (navbar)", "navbar" in html)
checar("favicon e logo da claquete no menu", "icon/favicon.svg" in html and "logo-marca" in html)
checar("link de pular conteúdo presente", "pular-conteudo" in html)
checar("painel de acessibilidade e assistente no layout", "acess-painel" in html and "ia-painel" in html)
checar("Bootstrap carregado", "bootstrap@5" in html)
for arq in ["favicon.svg", "favicon.ico", "favicon.png", "apple-touch-icon.png"]:
    checar(f"static/icon/{arq} servido", cliente.get(f"/static/icon/{arq}").status_code == 200)

shutil.rmtree(TMP, ignore_errors=True)
print("\n" + ("Todos os testes passaram." if falhas == 0 else f"{falhas} teste(s) falharam."))
sys.exit(1 if falhas else 0)
