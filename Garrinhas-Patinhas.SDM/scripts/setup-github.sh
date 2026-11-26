#!/usr/bin/env bash
# Cria labels, milestones (com as datas do cronograma) e issues no repositório.
# Pré-requisito: GitHub CLI instalado e autenticado (gh auth login). Rode DENTRO da pasta do repositório clonado.
set -euo pipefail
REPO="${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
echo "Repositório: $REPO"

# ---------- labels
for l in "backend:0e8a16" "frontend:1d76db" "api-governo:5319e7" "banco-de-dados:fbca04" "documentação:0075ca" "testes:d93f0b" "integração:b60205" "bug:d73a4a"; do
  gh label create "${l%%:*}" --color "${l##*:}" --force -R "$REPO" >/dev/null
done

# ---------- milestones (due_on = quinta-feira de cada semana, conforme cronograma)
mk() { gh api "repos/$REPO/milestones" -f title="$1" -f due_on="$2T23:59:00Z" -f description="$3" --jq '.number' 2>/dev/null \
       || gh api "repos/$REPO/milestones?state=all" --jq ".[] | select(.title==\"$1\") | .number"; }
M1=$(mk "Milestone 1 - Modelagem e Arquitetura"            2026-10-29 "Requisitos, MER/modelo relacional, arquitetura, repositório")
M2=$(mk "Milestone 2 - Banco de Dados e API Privada"       2026-11-05 "Banco implementado, CRUD, login, regras de integridade")
M3=$(mk "Milestone 3 - Interface Web e Funcionalidades"    2026-11-12 "Frontend, ViaCEP, animais/microchip, consultas e vacinas")
M4=$(mk "Milestone 4 - API Governamental e Integração"     2026-11-19 "API simulada, antirrábica, idempotência, falhas e reenvio")
M5=$(mk "Entrega Final - Testes, Documentação e Apresentação" 2026-11-26 "Testes completos, docs, instruções e apresentação")

# ---------- issues
iss() { gh issue create -R "$REPO" --title "$1" --body "$2" --label "$3" --milestone "$4" >/dev/null && echo "  + $1"; }
iss "Levantar e documentar requisitos funcionais e regras de negócio" "Ver docs/requisitos" "documentação" "Milestone 1 - Modelagem e Arquitetura"
iss "Modelar MER e modelo relacional (PK, FK, unicidade)"            "Ver docs/diagramas/modelo-relacional.md" "documentação,banco-de-dados" "Milestone 1 - Modelagem e Arquitetura"
iss "Definir tecnologias e desenhar a arquitetura (3 serviços)"      "Frontend, API privada, API governamental" "documentação" "Milestone 1 - Modelagem e Arquitetura"
iss "Organizar repositório Git (branches, templates, .gitignore)"    "main/develop, PR template, CONTRIBUTING" "documentação" "Milestone 1 - Modelagem e Arquitetura"
iss "Criar scripts do banco (schema + seed)"                         "database/clinica/*.sql" "banco-de-dados" "Milestone 2 - Banco de Dados e API Privada"
iss "CRUD de tutores, espécies, raças e animais"                     "" "backend" "Milestone 2 - Banco de Dados e API Privada"
iss "Autenticação: login, hash, confirmação, bloqueios, logout"      "JWT + scrypt" "backend" "Milestone 2 - Banco de Dados e API Privada"
iss "Coleção Postman inicial"                                        "postman/" "testes" "Milestone 2 - Banco de Dados e API Privada"
iss "Telas: login, tutores e animais"                                "frontend/" "frontend" "Milestone 3 - Interface Web e Funcionalidades"
iss "Consumo do ViaCEP com tratamento de erros"                      "CEP inexistente, timeout, indisponibilidade" "backend,frontend,integração" "Milestone 3 - Interface Web e Funcionalidades"
iss "Vínculo de microchip e histórico de substituição"               "" "backend,frontend" "Milestone 3 - Interface Web e Funcionalidades"
iss "Registro de consultas e vacinas + próximas doses"               "" "backend,frontend" "Milestone 3 - Interface Web e Funcionalidades"
iss "API governamental simulada (animais, vacinação, protocolos)"    "api-governo-simulada/" "api-governo" "Milestone 4 - API Governamental e Integração"
iss "Comunicação obrigatória da vacina antirrábica"                  "Após registro local; chave de idempotência" "backend,integração" "Milestone 4 - API Governamental e Integração"
iss "Controle de integrações, pendências e reenvio (manual/automático)" "Entidade IntegracaoGoverno" "backend,integração" "Milestone 4 - API Governamental e Integração"
iss "Simulação de indisponibilidade e timeout do governo"            "" "api-governo,testes" "Milestone 4 - API Governamental e Integração"
iss "Executar os 16 testes obrigatórios e gerar relatório"           "python tests/run_tests.py" "testes" "Entrega Final - Testes, Documentação e Apresentação"
iss "Documentação dos endpoints (OpenAPI)"                           "docs/api" "documentação" "Entrega Final - Testes, Documentação e Apresentação"
iss "Instruções de instalação e execução (README)"                   "" "documentação" "Entrega Final - Testes, Documentação e Apresentação"
iss "Preparar e ensaiar a apresentação do fluxo completo"            "Demonstrar: login → tutor/CEP → animal/chip → vacina antirrábica → falha → reenvio" "documentação" "Entrega Final - Testes, Documentação e Apresentação"
echo "Pronto. Crie o quadro em Projects (Kanban) e adicione as issues."
