# Relatório de testes executados

Execução: 23/11/2026 19:21 · Comando: `python tests/run_tests.py`

**Resultado: 25/25 verificações aprovadas.**

Ambiente: Python 3, Flask, SQLite; três serviços reais em portas de teste (clínica 18080, governo 18081) com bancos temporários. O ViaCEP foi substituído por um *mock* local porque o ambiente de execução não tinha acesso à internet; **repita o cenário 6 com o ViaCEP real** (`VIACEP_URL=https://viacep.com.br/ws`) antes da apresentação.

| # | Cenário | Resultado | Evidência |
|---|---|---|---|
| 1 | Login de veterinário ativo e com senha confirmada | ✅ Aprovado | HTTP 200, JWT emitido |
| 2 | Bloqueio de veterinário inativo | ✅ Aprovado | HTTP 403: Veterinário inativo. Acesso bloqueado. |
| 3 | Bloqueio de veterinário com senha não confirmada | ✅ Aprovado | HTTP 403: Senha não confirmada. Confirme o código enviado ao e-mail. |
| 4 | Rejeição de senha incorreta | ✅ Aprovado | HTTP 401: E-mail ou senha incorretos. |
| 5 | Cadastro de tutor e validação de CPF duplicado | ✅ Aprovado | cadastro HTTP 201; CPF repetido HTTP 409; CPF inválido HTTP 422 |
| 6 | Consulta de CEP válido e tratamento de CEP inexistente | ✅ Aprovado | válido HTTP 200; inexistente HTTP 404; formato inválido HTTP 422; timeout HTTP 504 |
| 6b | CEP: timeout do serviço externo tratado (504) | ✅ Aprovado | HTTP 504 |
| 7 | Cadastro de animal e vínculo de microchip | ✅ Aprovado | animal HTTP 201; microchip HTTP 201, vínculo pelo veterinário id=1; raça incompatível HTTP 422; sem raça HTTP 201 |
| 8 | Rejeição de microchip já utilizado | ✅ Aprovado | HTTP 409: Microchip já utilizado (vinculado a este ou a outro animal). |
| 9 | Registro de consulta e consulta ao histórico clínico | ✅ Aprovado | consulta HTTP 201; histórico com 1 item(ns) |
| 10 | Registro de vacina e consulta às próximas doses | ✅ Aprovado | vacina HTTP 201; próximas doses: ['2026-12-23'] |
| 11 | Cadastro e atualização de animal na API governamental simulada | ✅ Aprovado | governo HTTP 200; cadastro CONFIRMADA; cor no governo após PUT = Chocolate |
| 12 | Envio obrigatório de vacina antirrábica | ✅ Aprovado | integração CONFIRMADA, protocolo GOV-20261123-D8C7B6FD, 1 vacinação registrada no governo |
| 13 | Ausência de comunicação obrigatória para vacina não antirrábica | ✅ Aprovado | vacina polivalente: sem integração criada e 0 vacinações no governo |
| 14 | Indisponibilidade da API governamental e registro de pendência | ✅ Aprovado | vacina gravada localmente (HTTP 201); integração PENDENTE, tentativas=1, erro='Governo indisponível (HTTP 503).' |
| 15 | Reenvio de comunicação pendente e confirmação posterior | ✅ Aprovado | após reenvio: CONFIRMADA, protocolo GOV-20261123-CCCCE4B0, tentativas=2; governo com 2 vacinações (sem duplicar) |
| 16 | Repetição de solicitação sem duplicidade de vacinação no serviço externo | ✅ Aprovado | mesma chave -> duplicado=True, protocolo igual; chave diferente -> duplicado=True; reenvio pela clínica HTTP 200; vacinações no governo = 1 |
| E1 | Timeout na comunicação mantém pendência | ✅ Aprovado | status PENDENTE: Timeout na comunicação com o governo. |
| E2 | Reenvio automático regulariza pendências sem intervenção | ✅ Aprovado | status final CONFIRMADA |
| E3 | Antirrábica exige animal com microchip | ✅ Aprovado | HTTP 422 |
| E4 | Substituição de microchip preserva o histórico | ✅ Aprovado | 2 vínculos; anterior encerrado com motivo 'Chip danificado' |
| E5 | Endpoints privados exigem autenticação | ✅ Aprovado | GET /api/animais sem token -> 401 |
| E6 | Logout encerra a sessão (token revogado) | ✅ Aprovado | token após logout -> 401 |
| E7 | Fluxo de confirmação de senha (cadastro -> código -> login) | ✅ Aprovado | antes 403, depois 200 |
| E8 | Governo valida dados (422) e exige credencial (401) | ✅ Aprovado | inválido HTTP 422; sem chave HTTP 401 |

Os cenários numerados de 1 a 16 correspondem à seção 9 do enunciado; os demais (`6b`, `E1`…`E8`) são testes adicionais.
