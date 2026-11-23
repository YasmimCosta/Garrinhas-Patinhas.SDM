-- =====================================================================
-- Banco da CLÍNICA (SQLite, relacional). Portável para PostgreSQL/MySQL
-- trocando AUTOINCREMENT por SERIAL/AUTO_INCREMENT.
-- =====================================================================
PRAGMA foreign_keys = ON;

CREATE TABLE endereco (
  id_endereco  INTEGER PRIMARY KEY AUTOINCREMENT,
  cep          TEXT NOT NULL,
  logradouro   TEXT NOT NULL,
  numero       TEXT NOT NULL,
  complemento  TEXT,
  bairro       TEXT NOT NULL,
  cidade       TEXT NOT NULL,
  uf           TEXT NOT NULL CHECK (length(uf) = 2),
  codigo_ibge  TEXT
);

CREATE TABLE tutor (
  id_tutor         INTEGER PRIMARY KEY AUTOINCREMENT,
  id_endereco      INTEGER NOT NULL REFERENCES endereco(id_endereco),
  nome             TEXT NOT NULL,
  cpf              TEXT NOT NULL UNIQUE,
  data_nascimento  TEXT NOT NULL,
  telefone         TEXT NOT NULL,
  email            TEXT NOT NULL,
  data_cadastro    TEXT NOT NULL DEFAULT (datetime('now')),
  situacao         TEXT NOT NULL DEFAULT 'ATIVO' CHECK (situacao IN ('ATIVO','INATIVO'))
);

CREATE TABLE especie (
  id_especie  INTEGER PRIMARY KEY AUTOINCREMENT,
  nome        TEXT NOT NULL UNIQUE,
  descricao   TEXT,
  situacao    TEXT NOT NULL DEFAULT 'ATIVO' CHECK (situacao IN ('ATIVO','INATIVO'))
);

CREATE TABLE raca (
  id_raca     INTEGER PRIMARY KEY AUTOINCREMENT,
  id_especie  INTEGER NOT NULL REFERENCES especie(id_especie),
  nome        TEXT NOT NULL,
  porte       TEXT,
  descricao   TEXT,
  situacao    TEXT NOT NULL DEFAULT 'ATIVO' CHECK (situacao IN ('ATIVO','INATIVO')),
  UNIQUE (id_especie, nome)
);

CREATE TABLE veterinario (
  id_veterinario      INTEGER PRIMARY KEY AUTOINCREMENT,
  nome                TEXT NOT NULL,
  cpf                 TEXT NOT NULL UNIQUE,
  crmv                TEXT NOT NULL,
  crmv_uf             TEXT NOT NULL CHECK (length(crmv_uf) = 2),
  telefone            TEXT,
  email               TEXT NOT NULL UNIQUE,
  senha_hash          TEXT NOT NULL,
  senha_confirmada    INTEGER NOT NULL DEFAULT 0 CHECK (senha_confirmada IN (0,1)),
  codigo_confirmacao  TEXT,
  confirmada_em       TEXT,
  data_cadastro       TEXT NOT NULL DEFAULT (datetime('now')),
  situacao            TEXT NOT NULL DEFAULT 'ATIVO' CHECK (situacao IN ('ATIVO','INATIVO')),
  ultimo_acesso       TEXT,
  UNIQUE (crmv, crmv_uf)
);

-- tokens encerrados no logout (sessão)
CREATE TABLE token_revogado (
  jti          TEXT PRIMARY KEY,
  revogado_em  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE animal (
  id_animal             INTEGER PRIMARY KEY AUTOINCREMENT,
  id_tutor              INTEGER NOT NULL REFERENCES tutor(id_tutor),
  id_especie            INTEGER NOT NULL REFERENCES especie(id_especie),
  id_raca               INTEGER REFERENCES raca(id_raca),          -- NULL = sem raça definida
  nome                  TEXT NOT NULL,
  data_nascimento       TEXT,
  idade_estimada_meses  INTEGER,
  sexo                  TEXT NOT NULL CHECK (sexo IN ('M','F')),
  cor                   TEXT,
  peso_atual            REAL CHECK (peso_atual IS NULL OR peso_atual > 0),
  observacoes           TEXT,
  situacao              TEXT NOT NULL DEFAULT 'ATIVO' CHECK (situacao IN ('ATIVO','INATIVO','OBITO')),
  data_cadastro         TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK (data_nascimento IS NOT NULL OR idade_estimada_meses IS NOT NULL)
);

CREATE TABLE vinculo_microchip (
  id_vinculo        INTEGER PRIMARY KEY AUTOINCREMENT,
  id_animal         INTEGER NOT NULL REFERENCES animal(id_animal),
  id_veterinario    INTEGER NOT NULL REFERENCES veterinario(id_veterinario),
  codigo_microchip  TEXT NOT NULL UNIQUE,                 -- identificador RFID único
  data_inicio       TEXT NOT NULL DEFAULT (datetime('now')),
  data_fim          TEXT,
  motivo_fim        TEXT,
  observacao        TEXT
);
-- no máximo UM microchip ativo por animal (histórico preservado nos demais)
CREATE UNIQUE INDEX ux_vinculo_ativo ON vinculo_microchip(id_animal) WHERE data_fim IS NULL;

CREATE TABLE consulta (
  id_consulta     INTEGER PRIMARY KEY AUTOINCREMENT,
  id_animal       INTEGER NOT NULL REFERENCES animal(id_animal),
  id_veterinario  INTEGER NOT NULL REFERENCES veterinario(id_veterinario),
  data_hora       TEXT NOT NULL,
  motivo          TEXT NOT NULL,
  anamnese        TEXT,
  sintomas        TEXT,
  diagnostico     TEXT,
  tratamento      TEXT,
  prescricao      TEXT,
  peso            REAL CHECK (peso IS NULL OR peso > 0),
  temperatura     REAL,
  observacoes     TEXT,
  status          TEXT NOT NULL DEFAULT 'REALIZADA'
                  CHECK (status IN ('AGENDADA','REALIZADA','CANCELADA','NAO_COMPARECEU'))
);

CREATE TABLE vacina (
  id_vacina       INTEGER PRIMARY KEY AUTOINCREMENT,
  id_animal       INTEGER NOT NULL REFERENCES animal(id_animal),
  id_veterinario  INTEGER NOT NULL REFERENCES veterinario(id_veterinario),
  id_consulta     INTEGER REFERENCES consulta(id_consulta),
  nome            TEXT NOT NULL,
  tipo            TEXT NOT NULL CHECK (tipo IN ('ANTIRRABICA','POLIVALENTE','GRIPE','GIARDIA','OUTRA')),
  antirrabica     INTEGER NOT NULL DEFAULT 0 CHECK (antirrabica IN (0,1)),
  fabricante      TEXT NOT NULL,
  lote            TEXT NOT NULL,
  data_aplicacao  TEXT NOT NULL,
  dose            TEXT,
  via_aplicacao   TEXT,
  proxima_dose    TEXT,
  validade_lote   TEXT,
  observacoes     TEXT,
  status          TEXT NOT NULL DEFAULT 'APLICADA' CHECK (status IN ('AGENDADA','APLICADA','CANCELADA')),
  -- classificação estruturada: o flag é derivado do tipo, não do texto digitado
  CHECK (antirrabica = CASE WHEN tipo = 'ANTIRRABICA' THEN 1 ELSE 0 END)
);

CREATE TABLE integracao_governo (
  id_integracao       INTEGER PRIMARY KEY AUTOINCREMENT,
  id_animal           INTEGER NOT NULL REFERENCES animal(id_animal),
  id_vacina           INTEGER REFERENCES vacina(id_vacina),
  tipo_operacao       TEXT NOT NULL CHECK (tipo_operacao IN ('CADASTRO_ANIMAL','ATUALIZACAO_ANIMAL','VACINA_ANTIRRABICA')),
  servico             TEXT NOT NULL DEFAULT 'API_GOVERNO_SIMULADA',
  protocolo_externo   TEXT,
  chave_idempotencia  TEXT NOT NULL UNIQUE,
  solicitacao_json    TEXT NOT NULL,
  resposta_json       TEXT,
  status              TEXT NOT NULL DEFAULT 'PENDENTE'
                      CHECK (status IN ('PENDENTE','ENVIADA','CONFIRMADA','FALHA')),
  solicitado_em       TEXT NOT NULL,
  respondido_em       TEXT,
  tentativas          INTEGER NOT NULL DEFAULT 0,
  mensagem_erro       TEXT
);
CREATE INDEX ix_integracao_status ON integracao_governo(status);

CREATE INDEX ix_animal_tutor ON animal(id_tutor);
CREATE INDEX ix_consulta_animal ON consulta(id_animal);
CREATE INDEX ix_vacina_animal ON vacina(id_animal);
