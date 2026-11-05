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

CREATE TABLE IF NOT EXISTS anotacoes (
    id        TEXT PRIMARY KEY,
    filme_id  TEXT NOT NULL REFERENCES filmes(id) ON DELETE CASCADE,
    parte     TEXT,
    texto     TEXT NOT NULL,
    criado_em TEXT
);
