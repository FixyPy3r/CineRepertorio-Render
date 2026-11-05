"""Testes automatizados das rotas do CineRepertório (UC35) — usam uma cópia temporária do banco."""
import os
import shutil
import sqlite3
import sys
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp()
COPIA = os.path.join(TMP, "banco_teste.db")
shutil.copy(os.path.join(BASE, "banco.db"), COPIA)
os.environ["DATABASE"] = COPIA  # o app usa a cópia, o banco real fica intacto

sys.path.insert(0, BASE)
import app as aplicacao  # noqa: E402

cliente = aplicacao.app.test_client()
falhas = []


def consultar(sql, params=()):
    con = sqlite3.connect(COPIA)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def checar(rotulo, condicao):
    print(("  OK  " if condicao else " FALHA ") + rotulo)
    if not condicao:
        falhas.append(rotulo)


print("\n== GET ==")
for rota in ["/", "/filmes", "/filmes?tema=Educa%C3%A7%C3%A3o&ordem=ano",
             "/filmes?busca=educa%C3%A7%C3%A3o", "/filmes?parte=conclusao",
             "/filmes/parasita", "/filmes/novo", "/filmes/parasita/editar",
             "/anotacoes", "/estrutura", "/sobre"]:
    r = cliente.get(rota)
    checar(f"GET {rota} -> {r.status_code}", r.status_code == 200)
checar("GET /filmes/inexistente -> 404", cliente.get("/filmes/inexistente").status_code == 404)

print("\n== BUSCA / FILTROS (SQL) ==")
checar("filtro por tema Educação retorna só filmes com esse tema",
       all("Educação" in f["temas"] for f in aplicacao.app.test_client().get("/api/filmes?tema=Educa%C3%A7%C3%A3o").get_json()["filmes"]))
checar("busca ignora maiúsculas e acentos de caixa (EDUCAÇÃO)",
       cliente.get("/api/filmes?busca=EDUCA%C3%87%C3%83O").get_json()["total"] > 0)
checar("ordem por ano é decrescente", (lambda l: l == sorted(l, reverse=True))(
    [f["ano"] for f in cliente.get("/api/filmes?ordem=ano").get_json()["filmes"]]))

print("\n== API JSON ==")
r = cliente.get("/api/filmes")
dados = r.get_json()
checar("GET /api/filmes devolve JSON com 52 filmes", r.is_json and dados["total"] == 52)
checar("cada filme traz lista de temas", all(isinstance(f["temas"], list) and f["temas"] for f in dados["filmes"]))
r = cliente.get("/api/filmes/parasita")
checar("GET /api/filmes/parasita devolve o filme", r.status_code == 200 and r.get_json()["titulo"] == "Parasita")
checar("GET /api/filmes/xxx -> 404 em JSON", cliente.get("/api/filmes/xxx").status_code == 404)

print("\n== CREATE ==")
cliente.post("/filmes/novo", data={
    "titulo": "Filme de Teste UC35", "ano": "2024", "diretor": "Equipe de Testes",
    "imdb": "8.2", "temas": "Educação, Tecnologia, Tema Inédito",
    "sinopse": "Filme criado automaticamente para validar o cadastro do sistema.",
    "comoUsar": "Usado apenas em teste automatizado.",
    "citacao": "Filme de Teste UC35 (2024) comprova que o cadastro funciona corretamente.",
    "parte": "desenvolvimento", "cartaz": "",
}, follow_redirects=True)
checar("POST /filmes/novo cria registro no banco",
       consultar("SELECT COUNT(*) FROM filmes WHERE id='filme-de-teste-uc35'")[0][0] == 1)
checar("temas gravados na tabela de relação (3 vínculos)",
       consultar("SELECT COUNT(*) FROM filme_temas WHERE filme_id='filme-de-teste-uc35'")[0][0] == 3)
checar("tema novo criado na tabela temas",
       consultar("SELECT COUNT(*) FROM temas WHERE nome='Tema Inédito'")[0][0] == 1)

print("\n== VALIDAÇÃO ==")
antes = consultar("SELECT COUNT(*) FROM filmes")[0][0]
cliente.post("/filmes/novo", data={"titulo": "", "ano": "abc", "diretor": "", "imdb": "99",
                                   "temas": "", "sinopse": "curta", "citacao": "curta", "parte": "x"})
checar("POST inválido é rejeitado", antes == consultar("SELECT COUNT(*) FROM filmes")[0][0])

print("\n== UPDATE ==")
cliente.post("/filmes/filme-de-teste-uc35/editar", data={
    "titulo": "Filme de Teste UC35", "ano": "2025", "diretor": "Equipe de Testes",
    "imdb": "9.0", "temas": "Educação", "sinopse": "Sinopse atualizada pelo teste automatizado.",
    "comoUsar": "", "citacao": "Citação atualizada pelo teste automatizado do sistema.",
    "parte": "conclusao", "cartaz": "",
}, follow_redirects=True)
checar("POST editar atualiza ano e nota",
       consultar("SELECT ano, imdb FROM filmes WHERE id='filme-de-teste-uc35'") == [(2025, 9.0)])
checar("editar substitui os temas (agora 1)",
       consultar("SELECT COUNT(*) FROM filme_temas WHERE filme_id='filme-de-teste-uc35'")[0][0] == 1)
checar("tema que ficou sem filmes é removido",
       consultar("SELECT COUNT(*) FROM temas WHERE nome='Tema Inédito'")[0][0] == 0)

print("\n== ANOTAÇÕES (JOIN) ==")
cliente.post("/anotacoes", data={"filme_id": "parasita", "parte": "introducao",
                                 "texto": "Usar Parasita para falar de desigualdade espacial."},
             follow_redirects=True)
anots = consultar("SELECT id FROM anotacoes")
checar("POST /anotacoes cria anotação", len(anots) == 1)
checar("anotação aparece na página do filme", "desigualdade espacial" in cliente.get("/filmes/parasita").get_data(as_text=True))
checar("anotação traz o título do filme via JOIN",
       cliente.get("/api/filmes/parasita").get_json()["anotacoes"][0]["filme_titulo"] == "Parasita")
if anots:
    cliente.post(f"/anotacoes/{anots[0][0]}/excluir", follow_redirects=True)
    checar("POST excluir anotação", consultar("SELECT COUNT(*) FROM anotacoes")[0][0] == 0)

print("\n== DELETE (CASCADE) ==")
cliente.post("/anotacoes", data={"filme_id": "filme-de-teste-uc35", "parte": "conclusao",
                                 "texto": "Anotação que deve sumir junto com o filme."})
cliente.post("/filmes/filme-de-teste-uc35/excluir", follow_redirects=True)
checar("POST excluir remove o filme", consultar("SELECT COUNT(*) FROM filmes WHERE id='filme-de-teste-uc35'")[0][0] == 0)
checar("vínculos de tema removidos em cascata",
       consultar("SELECT COUNT(*) FROM filme_temas WHERE filme_id='filme-de-teste-uc35'")[0][0] == 0)
checar("anotações do filme removidas em cascata",
       consultar("SELECT COUNT(*) FROM anotacoes WHERE filme_id='filme-de-teste-uc35'")[0][0] == 0)
checar("catálogo original preservado (52 filmes)", consultar("SELECT COUNT(*) FROM filmes")[0][0] == 52)
checar("nenhuma chave estrangeira quebrada", consultar("PRAGMA foreign_key_check") == [])

print("\n== HERANÇA DE TEMPLATES / ACESSIBILIDADE ==")
html = cliente.get("/filmes").get_data(as_text=True)
checar("base.html aplicado (navbar em todas as páginas)", "Cine" in html and "navbar" in html)
checar("link de pular conteúdo presente", "pular-conteudo" in html)
checar("Bootstrap carregado", "bootstrap@5" in html)

shutil.rmtree(TMP, ignore_errors=True)
print("\n" + ("TODOS OS TESTES PASSARAM" if not falhas else f"FALHAS: {falhas}"))
sys.exit(1 if falhas else 0)
