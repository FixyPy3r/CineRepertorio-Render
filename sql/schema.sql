CREATE TABLE IF NOT EXISTS filmes (
    id        TEXT PRIMARY KEY,
    titulo    TEXT NOT NULL,
    ano       INTEGER,
    diretor   TEXT,
    imdb      REAL,
    sinopse   TEXT,
    como_usar TEXT,
    citacao   TEXT,
    parte     TEXT CHECK (parte IN ('introducao','desenvolvimento','conclusao')),
    cor       TEXT,
    cartaz    TEXT
);

CREATE TABLE IF NOT EXISTS temas (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS filme_temas (
    filme_id TEXT    NOT NULL REFERENCES filmes(id) ON DELETE CASCADE,
    tema_id  INTEGER NOT NULL REFERENCES temas(id)  ON DELETE CASCADE,
    PRIMARY KEY (filme_id, tema_id)
);

CREATE TABLE IF NOT EXISTS usuarios (
    id         TEXT PRIMARY KEY,
    nome       TEXT NOT NULL,
    sobrenome  TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    salt       TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    a2f        INTEGER NOT NULL DEFAULT 0 CHECK (a2f IN (0,1)),
    iniciais   TEXT,
    criado_em  TEXT
);

CREATE TABLE IF NOT EXISTS anotacoes (
    id         TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    filme_id   TEXT NOT NULL REFERENCES filmes(id)   ON DELETE CASCADE,
    parte      TEXT,
    texto      TEXT NOT NULL,
    criado_em  TEXT
);

CREATE INDEX IF NOT EXISTS idx_anotacoes_usuario ON anotacoes(usuario_id);
CREATE INDEX IF NOT EXISTS idx_anotacoes_filme   ON anotacoes(filme_id);
