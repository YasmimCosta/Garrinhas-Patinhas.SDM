# Modelo de dados — Clínica Veterinária Garrinhas & Patinhas

Baseado no diagrama da equipe (`diagrama-er-original-v2.pdf`) e ajustado para cobrir **todos** os atributos
e regras do enunciado (seções 3, 5 e 6). O script executável está em [`database/clinica/01_schema.sql`](../../database/clinica/01_schema.sql).

## Diagrama entidade-relacionamento

```mermaid
erDiagram
    ENDERECO ||--o{ TUTOR : "residência (1:N)"
    TUTOR ||--o{ ANIMAL : "possui (1:N)"
    ESPECIE ||--o{ RACA : "classifica (1:N)"
    ESPECIE ||--o{ ANIMAL : "define (1:N)"
    RACA |o--o{ ANIMAL : "raça opcional"
    ANIMAL ||--o{ VINCULO_MICROCHIP : "histórico de vínculos (1:N)"
    VETERINARIO ||--o{ VINCULO_MICROCHIP : "realiza o vínculo (1:N)"
    ANIMAL ||--o{ CONSULTA : "recebe (1:N)"
    VETERINARIO ||--o{ CONSULTA : "atende (1:N)"
    ANIMAL ||--o{ VACINA : "recebe (1:N)"
    VETERINARIO ||--o{ VACINA : "aplica (1:N)"
    CONSULTA |o--o{ VACINA : "pode originar (0..N)"
    ANIMAL ||--o{ INTEGRACAO_GOVERNO : "gera (1:N)"
    VACINA |o--o| INTEGRACAO_GOVERNO : "antirrábica gera (0..1)"

    ENDERECO { int id_endereco PK
      string cep
      string logradouro
      string numero
      string complemento
      string bairro
      string cidade
      string uf
      string codigo_ibge }
    TUTOR { int id_tutor PK
      int id_endereco FK
      string nome
      string cpf UK
      date data_nascimento
      string telefone
      string email
      datetime data_cadastro
      string situacao }
    ESPECIE { int id_especie PK
      string nome UK
      string descricao
      string situacao }
    RACA { int id_raca PK
      int id_especie FK
      string nome
      string porte
      string descricao
      string situacao }
    VETERINARIO { int id_veterinario PK
      string nome
      string cpf UK
      string crmv
      string crmv_uf
      string email UK
      string telefone
      string senha_hash
      bool senha_confirmada
      string codigo_confirmacao
      datetime confirmada_em
      string situacao
      datetime ultimo_acesso }
    ANIMAL { int id_animal PK
      int id_tutor FK
      int id_especie FK
      int id_raca FK "nullable"
      string nome
      date data_nascimento
      int idade_estimada_meses
      string sexo
      string cor
      decimal peso_atual
      string situacao }
    VINCULO_MICROCHIP { int id_vinculo PK
      int id_animal FK
      int id_veterinario FK
      string codigo_microchip UK
      datetime data_inicio
      datetime data_fim
      string motivo_fim }
    CONSULTA { int id_consulta PK
      int id_animal FK
      int id_veterinario FK
      datetime data_hora
      string motivo
      string anamnese
      string sintomas
      string diagnostico
      string tratamento
      string prescricao
      decimal peso
      decimal temperatura
      string status }
    VACINA { int id_vacina PK
      int id_animal FK
      int id_veterinario FK
      int id_consulta FK "nullable"
      string nome
      string tipo
      bool antirrabica
      string fabricante
      string lote
      date data_aplicacao
      string dose
      string via_aplicacao
      date proxima_dose
      date validade_lote
      string status }
    INTEGRACAO_GOVERNO { int id_integracao PK
      int id_animal FK
      int id_vacina FK "nullable"
      string tipo_operacao
      string protocolo_externo
      string chave_idempotencia UK
      string status
      datetime solicitado_em
      datetime respondido_em
      int tentativas
      string mensagem_erro }
```

## Chaves, unicidade e restrições

| Tabela | PK | FKs | Unicidade | Restrições (CHECK / índice) |
|---|---|---|---|---|
| endereco | id_endereco | — | — | `length(uf)=2` |
| tutor | id_tutor | id_endereco | **cpf** | situação ∈ {ATIVO, INATIVO} |
| especie | id_especie | — | **nome** | situação |
| raca | id_raca | id_especie | **(id_especie, nome)** | situação |
| veterinario | id_veterinario | — | **cpf**, **email**, **(crmv, crmv_uf)** | senha_confirmada ∈ {0,1}; situação |
| animal | id_animal | id_tutor (NOT NULL), id_especie, id_raca (NULL = sem raça) | — | sexo ∈ {M,F}; peso > 0; **data_nascimento OU idade_estimada** |
| vinculo_microchip | id_vinculo | id_animal, id_veterinario | **codigo_microchip** | índice único parcial: **1 microchip ativo por animal** (`data_fim IS NULL`) |
| consulta | id_consulta | id_animal, id_veterinario | — | status ∈ {AGENDADA, REALIZADA, CANCELADA, NAO_COMPARECEU} |
| vacina | id_vacina | id_animal, id_veterinario, id_consulta (NULL) | — | tipo estruturado; `antirrabica = (tipo='ANTIRRABICA')`; status ∈ {AGENDADA, APLICADA, CANCELADA} |
| integracao_governo | id_integracao | id_animal, id_vacina (NULL) | **chave_idempotencia** | tipo_operacao; status ∈ {PENDENTE, ENVIADA, CONFIRMADA, FALHA} |

## O que foi ajustado em relação ao diagrama original (v2)

O diagrama da equipe estava correto na estrutura geral. Para atender ao enunciado, foram acrescentados/corrigidos:

| Entidade | Ajuste | Motivo (enunciado) |
|---|---|---|
| **Veterinário** | + `cpf`, `crmv_uf`, `senha_hash`, `senha_confirmada`, `codigo_confirmacao`, `confirmada_em`, `situacao`, `ultimo_acesso`, `data_cadastro` | 3.1 e 3.6: login, hash, confirmação, bloqueio de inativos |
| **Tutor** | + `data_nascimento`, `situacao` | 3.2: inativar tutor |
| **Endereço** | + `codigo_ibge` | 3.3 |
| **Espécie / Raça** | + `situacao` (ambas), `descricao` (raça) | 3.4 e 3.5 |
| **Animal** | + `id_especie` (e `id_raca` agora **nullable**), `cor`, `idade_estimada_meses`, `situacao` | 3.5/3.7: "sem raça definida" não pode perder a espécie |
| **Consulta** | + `anamnese`, `sintomas`, `tratamento`, `peso`, `temperatura`, `observacoes` | 3.8 |
| **Vacina** | + `tipo`, `antirrabica`, `via_aplicacao`, `dose`, `validade_lote`, `status`; `id_consulta` opcional | 3.9: classificação estruturada da antirrábica |
| **Integração_Governo** | FK `id_consulta` → **`id_vacina`**; + `tentativas`, `mensagem_erro`, `tipo_operacao` (substitui `servico`) | Seção 5: vínculo com a aplicação de vacina e controle de tentativas |
| **Vínculo_Microchip** | `codigo_microchip` UNIQUE + índice parcial do chip ativo | 3.7: unicidade e histórico na substituição |

> ✏️ **A fazer pela equipe:** atualizar o diagrama visual (PDF/imagem) com estes ajustes e salvá-lo nesta pasta.
> O diagrama Mermaid acima já serve como entrega (o GitHub o renderiza).
