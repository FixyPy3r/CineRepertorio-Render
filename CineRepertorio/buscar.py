"""Busca cartazes no TMDB e grava no campo `cartaz` do banco.db.

Uso (na pasta do projeto, onde está o banco.db):
    1) A chave já está abaixo (ou use a variável de ambiente TMDB_KEY).
    2) Teste sem gravar:        python buscar_cartazes_tmdb.py
    3) Grave de verdade:        python buscar_cartazes_tmdb.py --aplicar
    Só filmes SEM cartaz:       python buscar_cartazes_tmdb.py --aplicar --so-vazios
    Um filme só (teste):        python buscar_cartazes_tmdb.py --id parasita
    Por padrão só grava os OK; os CONFIRA ficam de fora (use --aceitar-incertos para gravá-los).

Não precisa instalar nada: usa só a biblioteca padrão do Python.
"""

import argparse
import json
import os
import sqlite3
import time
import urllib.parse
import urllib.request

CHAVE = os.environ.get("TMDB_KEY", "").strip()
TAMANHO = "w500"  # w342 = mais leve | w500 = bom | w780 = grande
BANCO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banco.db")


def buscar(titulo, ano):
    """Devolve (poster_path, titulo_tmdb, ano_tmdb) ou None."""
    url = "https://api.themoviedb.org/3/search/movie?" + urllib.parse.urlencode(
        {"api_key": CHAVE, "query": titulo, "language": "pt-BR", "include_adult": "false"}
    )
    with urllib.request.urlopen(url, timeout=20) as r:
        resultados = json.load(r).get("results", [])

    com_cartaz = [x for x in resultados if x.get("poster_path")]

    def ano_do(x):
        data = x.get("release_date") or ""
        return int(data[:4]) if data[:4].isdigit() else None

    # 1º: mesmo ano (±1). 2º: primeiro resultado com cartaz (marcado como "incerto").
    for x in com_cartaz:
        if ano and ano_do(x) and abs(ano_do(x) - ano) <= 1:
            return x["poster_path"], x.get("title"), ano_do(x), True
    if com_cartaz:
        x = com_cartaz[0]
        return x["poster_path"], x.get("title"), ano_do(x), False
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true", help="grava no banco (sem isso, só mostra)")
    ap.add_argument("--so-vazios", action="store_true", help="ignora filmes que já têm cartaz")
    ap.add_argument("--id", help="processa só este id (ex.: parasita)")
    ap.add_argument("--aceitar-incertos", action="store_true",
                    help="grava também os CONFIRA (ano diferente; pode ser outro filme)")
    args = ap.parse_args()

    if not CHAVE or CHAVE in {"COLE_SUA_CHAVE_AQUI", "COLOQUE_SUA_CHAVE_TMDB_AQUI"}:
        raise SystemExit("Cole sua chave do TMDB na variável CHAVE (ou use TMDB_KEY).")

    con = sqlite3.connect(BANCO)
    sql = "SELECT id, titulo, ano, COALESCE(cartaz,'') FROM filmes"
    filtros, params = [], []
    if args.id:
        filtros.append("id = ?")
        params.append(args.id)
    if args.so_vazios:
        filtros.append("COALESCE(cartaz,'') = ''")
    if filtros:
        sql += " WHERE " + " AND ".join(filtros)
    filmes = con.execute(sql + " ORDER BY rowid", params).fetchall()

    achados = incertos = faltou = 0
    for id_, titulo, ano, atual in filmes:
        try:
            r = buscar(titulo, ano)
        except Exception as erro:  # rede, chave inválida etc.
            print(f"ERRO   {titulo}: {erro}")
            faltou += 1
            continue
        if not r:
            print(f"SEM    {titulo} ({ano}) — nada encontrado")
            faltou += 1
        else:
            path, t_tmdb, a_tmdb, certo = r
            link = f"https://image.tmdb.org/t/p/{TAMANHO}{path}"
            marca = "OK    " if certo else "CONFIRA"
            print(f"{marca} {titulo} ({ano}) -> {t_tmdb} ({a_tmdb})  {link}")
            achados += certo
            incertos += not certo
            if args.aplicar and (certo or args.aceitar_incertos):
                con.execute("UPDATE filmes SET cartaz = ? WHERE id = ?", (link, id_))
        time.sleep(0.12)  # respeita o limite de requisições do TMDB

    if args.aplicar:
        con.commit()
    restantes = con.execute(
        "SELECT id, titulo, ano FROM filmes WHERE cartaz LIKE '%wikipedia.org%' OR cartaz LIKE '%wikimedia.org%' ORDER BY rowid"
    ).fetchall()
    con.close()
    print(f"\n{achados} certos | {incertos} para conferir | {faltou} sem resultado"
          + ("" if args.aplicar else "  (nada foi gravado; use --aplicar)"))
    if restantes:
        print(f"\nAinda com link da Wikipédia/Wikimedia ({len(restantes)}):")
        for id_, titulo, ano in restantes:
            print(f"  - {titulo} ({ano})  [id: {id_}]")
    else:
        print("\nNenhum filme com link da Wikipédia: todos usam o TMDB.")


if __name__ == "__main__":
    main()