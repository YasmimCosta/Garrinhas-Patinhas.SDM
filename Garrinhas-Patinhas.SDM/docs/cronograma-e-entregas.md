# Cronograma × entregas

Cronograma do professor (`docs/cronograma.jpeg`): 5 semanas, milestones às quintas-feiras, entrega final em **26/11/2026**.

| Milestone | Data | Peso | Tema | Status no repositório |
|---|---|---|---|---|
| 1 | 29/10 | — | Modelagem e Arquitetura | ✅ Entregáveis prontos (ajustar diagrama visual) |
| 2 | 05/11 | 20% | Banco de Dados e API Privada | ✅ Código pronto e testado |
| 3 | 12/11 | 20% | Interface Web e Funcionalidades Clínicas | ✅ Código pronto (validar ViaCEP real) |
| 4 | 19/11 | 25% | API Governamental e Integração Distribuída | ✅ Código pronto e testado |
| Final | 26/11 | 25% | Testes, Documentação e Apresentação | 🔶 Falta: repetir testes na máquina, diagrama visual, apresentação |

## Milestone 1 — Modelagem e Arquitetura (29/10)
| Atividade do cronograma | Arquivo |
|---|---|
| Requisitos e regras de negócio | `docs/requisitos/requisitos-e-arquitetura.md` |
| MER e modelo relacional | `docs/diagramas/modelo-relacional.md` (+ `diagrama-er-original-v2.pdf`) |
| Definição de tecnologias e arquitetura | mesmo documento de requisitos (seção "Decisões tecnológicas") |
| Repositório Git e ambiente | `.gitignore`, `.env.example`, `requirements.txt`, `.github/`, `CONTRIBUTING.md` |

## Milestone 2 — Banco de Dados e API Privada (05/11)
| Atividade | Arquivo |
|---|---|
| Tabelas e entidades | `database/clinica/01_schema.sql`, `02_seed.sql` |
| CRUD das entidades | `backend-clinica/app.py` |
| Login, controle de acesso, senha | `backend-clinica/security.py`, `/api/auth/*` |
| Regras de integridade | constraints do schema + validações em `app.py` |
| Coleção de testes | `postman/Clinica-Veterinaria.postman_collection.json` |

## Milestone 3 — Interface Web e Funcionalidades Clínicas (12/11)
| Atividade | Arquivo |
|---|---|
| Telas web | `frontend/index.html`, `style.css`, `app.js` |
| ViaCEP | `backend-clinica/viacep.py` + botão "Buscar CEP" |
| Animal e vínculo de microchip | `/api/animais/{id}/microchip` + tela de detalhe |
| Consultas e vacinas, históricos | `/api/consultas`, `/api/vacinas` |

## Milestone 4 — API Governamental e Integração (19/11)
| Atividade | Arquivo |
|---|---|
| API governamental simulada | `api-governo-simulada/app.py`, `database/governo/01_schema.sql` |
| Cadastro/atualização/recebimento de vacina | endpoints `/api/governo/*` |
| Controle de integração, protocolos e status | tabela `integracao_governo`, `backend-clinica/integracao.py` |
| Indisponibilidade, reenvio e idempotência | modo 503/timeout, reenvio manual e automático, `Idempotency-Key` |

## Entrega Final (26/11)
| Atividade | Arquivo / ação |
|---|---|
| Testes integrados | `python tests/run_tests.py` → `docs/testes/relatorio-testes.md` |
| Documentação dos endpoints | `docs/api/openapi-*.yaml` |
| Instruções de execução | `README.md` |
| Apresentação | roteiro abaixo |


