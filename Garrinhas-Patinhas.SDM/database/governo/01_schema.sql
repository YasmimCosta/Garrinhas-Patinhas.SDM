-- Banco da API GOVERNAMENTAL SIMULADA (independente do banco da clínica)
CREATE TABLE animal_gov (
  id_animal_gov     INTEGER PRIMARY KEY AUTOINCREMENT,
  microchip         TEXT NOT NULL UNIQUE,
  id_animal_origem  INTEGER,
  nome              TEXT NOT NULL,
  especie           TEXT NOT NULL,
  raca              TEXT,
  sexo              TEXT NOT NULL,
  data_nascimento   TEXT,
  cor               TEXT,
  tutor_nome        TEXT NOT NULL,
  tutor_cpf         TEXT NOT NULL,
  responsavel_crmv  TEXT,
  microchip_anterior TEXT,
  criado_em         TEXT NOT NULL,
  atualizado_em     TEXT NOT NULL
);

CREATE TABLE vacinacao_antirrabica (
  id_vacinacao      INTEGER PRIMARY KEY AUTOINCREMENT,
  microchip         TEXT NOT NULL,
  id_animal_origem  INTEGER,
  nome_animal       TEXT,
  data_aplicacao    TEXT NOT NULL,
  vacina_nome       TEXT NOT NULL,
  fabricante        TEXT NOT NULL,
  lote              TEXT NOT NULL,
  veterinario_nome  TEXT,
  veterinario_crmv  TEXT NOT NULL,
  tutor_nome        TEXT,
  tutor_cpf         TEXT,
  protocolo         TEXT NOT NULL,
  criado_em         TEXT NOT NULL,
  UNIQUE (microchip, data_aplicacao, lote)     -- impede duplicidade de vacinação
);

CREATE TABLE operacao (
  protocolo           TEXT PRIMARY KEY,
  tipo                TEXT NOT NULL,
  microchip           TEXT,
  status              TEXT NOT NULL,
  chave_idempotencia  TEXT UNIQUE,              -- reenvio com a mesma chave = mesma resposta
  resposta_json       TEXT NOT NULL,
  criado_em           TEXT NOT NULL
);

CREATE TABLE configuracao (
  chave  TEXT PRIMARY KEY,
  valor  TEXT NOT NULL
);
INSERT INTO configuracao VALUES ('indisponibilidade', 'off');
