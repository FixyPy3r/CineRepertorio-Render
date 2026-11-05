# CineRepertório

Aplicação web em **Flask + SQLite** que reúne filmes utilizáveis como **repertório sociocultural**
na redação do ENEM: nota do IMDb, sinopse, temas, parágrafo ideal, citação pronta,
links para assistir e anotações pessoais do estudante.

Projeto da **UC35 — Projeto Integrador Back-end**.

## Como executar

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Acesse: http://localhost:5000

## Banco de dados (SQLite)

Arquivo `banco.db`, já com os 52 filmes. As tabelas são criadas por `sql/schema.sql`
(o app as cria sozinho se o arquivo estiver vazio) e os dados de exemplo estão em
`sql/dados_iniciais.sql`.

```
filmes (id PK, titulo, ano, diretor, imdb, sinopse, como_usar, citacao, parte, cor, cartaz)
temas (id PK, nome UNIQUE)
filme_temas (filme_id FK→filmes, tema_id FK→temas, PK composta)   -- N:N filmes x temas
anotacoes (id PK, filme_id FK→filmes, parte, texto, criado_em)    -- 1:N filmes x anotações
```

Para recriar o banco do zero:

```bash
rm banco.db
sqlite3 banco.db < sql/schema.sql
sqlite3 banco.db < sql/dados_iniciais.sql
```

## Estrutura do projeto

```
cinerepertorio/
├── app.py              # rotas, regras e acesso ao banco
├── banco.db            # banco SQLite com dados de exemplo
├── sql/
│   ├── schema.sql          # criação das tabelas
│   └── dados_iniciais.sql  # INSERTs dos 52 filmes
├── requirements.txt    # flask, gunicorn
├── Procfile            # web: gunicorn app:app  (Render)
├── testes.py           # testes automatizados (usam cópia do banco)
├── static/             # CSS, JS e imagens
└── templates/          # base.html + páginas (herança Jinja2)
```

## Rotas

| Rota | Métodos | Função |
|---|---|---|
| `/` | GET | Página inicial |
| `/filmes` | GET | Catálogo com busca, filtro e ordenação (READ, SQL com JOIN) |
| `/filmes/<id>` | GET | Detalhe do filme, relacionados (JOIN) e anotações |
| `/filmes/novo` | GET, POST | Cadastro (CREATE) |
| `/filmes/<id>/editar` | GET, POST | Edição (UPDATE) |
| `/filmes/<id>/excluir` | POST | Exclusão (DELETE, em cascata) |
| `/anotacoes` | GET, POST | Anotações (READ e CREATE, JOIN com filmes) |
| `/anotacoes/<id>/excluir` | POST | Exclusão de anotação |
| `/estrutura` | GET | Guia da estrutura da redação |
| `/sobre` | GET | Documentação |
| `/api/filmes` | GET | **JSON**: lista de filmes (`?busca=`, `?tema=`, `?parte=`, `?ordem=`) |
| `/api/filmes/<id>` | GET | **JSON**: um filme com temas e anotações |

## Testes

```bash
python testes.py
```

## Deploy no Render

1. Suba o projeto para um repositório no GitHub (com `banco.db`, `requirements.txt` e `Procfile`).
2. No Render: **New → Web Service**, conecte o repositório.
3. Build command: `pip install -r requirements.txt` · Start command: `gunicorn app:app`.

> No plano gratuito do Render o disco é temporário: cadastros feitos online voltam ao
> estado do `banco.db` do repositório quando o serviço reinicia ou é publicado de novo.

## Acessibilidade

Link "pular para o conteúdo", HTML semântico, `alt` em todas as imagens,
`label` em todos os campos, avisos com `aria-live`, foco visível, alto contraste,
animações que param no hover/foco e respeito a `prefers-reduced-motion`.
