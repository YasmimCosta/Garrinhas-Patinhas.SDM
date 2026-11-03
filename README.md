# Garrinhas&Patinhas - SDM
Desesnvolvimento de um sistema de web com integração de APIs (privadas, públicas e governamental simulada) de um sistema de gestão de clínica veterinária para projeto SDM.

# 🐾 Sistema Web para Gestão de Clínica Veterinária com Integração de APIs

> **A3 – Projeto Integrador · Sistemas Distribuídos e Mobile (SDM)**
> IBMR Centro Universitário · Apresentação/Entrega: **26/11/2026**

![status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![license](https://img.shields.io/badge/licen%C3%A7a-MIT-blue)

---

## 📖 Sobre o projeto

Sistema web para informatizar o cadastro e o atendimento de uma clínica veterinária, permitindo gerenciar **tutores, animais, veterinários, consultas e vacinas**.

A solução é composta por três serviços que se comunicam via HTTP:

1. **API privada da clínica**: regras de negócio, autenticação, validações e persistência.
2. **API pública real (ViaCEP)**: consulta de CEP para preenchimento automático de endereços.
3. **API governamental simulada**: serviço independente que simula o registro de animais identificados por **microchip RFID** e recebe as comunicações obrigatórias de **vacina antirrábica**.

O projeto demonstra conceitos de desenvolvimento web, APIs REST, sistemas distribuídos, integração entre serviços, persistência de dados, autenticação e tratamento de falhas de comunicação.

## 🎯 Objetivos

Desenvolver um sistema web com banco de dados próprio, API privada, consumo de API pública real e integração com API governamental simulada, garantindo:

- controle de acesso;
- rastreabilidade dos procedimentos;
- comunicação das informações obrigatórias.

## 🛠️ Tecnologias

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Frontend | _a definir_ | _a definir_ |
| Backend (API privada) | _a definir_ | _a definir_ |
| API governamental simulada | _a definir_ | _a definir_ |
| Banco de dados | _PostgreSQL / MySQL_ | _a definir_ |
| Documentação da API | Swagger / OpenAPI | Documentação padronizada dos endpoints |
| Testes de API | Postman | Coleção de testes reproduzível |
| Controle de versão | Git + GitHub | Colaboração e rastreabilidade |

## ✅ Funcionalidades

### Autenticação e controle de acesso
- Login por e-mail e senha
- Senha armazenada com **hash** apropriado (nunca em texto puro)
- Confirmação de senha por código/link enviado por e-mail (pode ser simulado)
- Bloqueio de veterinários **inativos** ou com **senha não confirmada**
- Logout e encerramento de sessão
- Proteção de todos os endpoints privados

### Cadastros
- **Tutores**: incluir, consultar, alterar e inativar (CPF validado e único)
- **Endereços**: preenchimento automático via ViaCEP, com complemento manual e tratamento de CEP inexistente, timeout e indisponibilidade
- **Espécies** e **Raças**: catálogo com validação de compatibilidade raça × espécie (permite "sem raça definida")
- **Veterinários**: CRMV, UF, situação, confirmação de senha e último acesso
- **Animais e microchip RFID**: microchip único, vinculado por veterinário autenticado, com histórico preservado em caso de substituição

### Atendimento
- **Consultas**: anamnese, sintomas, diagnóstico, tratamento, prescrição, peso, temperatura e situação (agendada, realizada, cancelada, não compareceu)
- **Vacinas**: dados do lote, fabricante, dose, via de aplicação, próxima dose e situação (agendada, aplicada, cancelada)
- Histórico de consultas e vacinação por animal, com próximas doses previstas

## 📁 Estrutura do repositório

```
clinica-veterinaria/
├── frontend/                  # Interface web
│   └── src/
├── backend-clinica/           # API privada
│   ├── src/
│   └── tests/
├── api-governo-simulada/      # API governamental simulada
│   ├── src/
│   └── tests/
├── database/                  # Scripts de criação e carga inicial
│   ├── clinica/
│   └── governo/
├── docs/
│   ├── requisitos/
│   ├── diagramas/             # DER, modelo relacional, arquitetura
│   ├── api/                   # OpenAPI/Swagger
│   └── testes/                # Relatório de testes
├── postman/                   # Coleção de testes das APIs
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## 🚀 Como executar

> Ainda temos que atualizar

## 🧪 Testes

**Autenticação**
- [ ] 1. Login de veterinário ativo e com senha confirmada
- [ ] 2. Bloqueio de veterinário inativo
- [ ] 3. Bloqueio de veterinário com senha não confirmada
- [ ] 4. Rejeição de senha incorreta

**Cadastros**
- [ ] 5. Cadastro de tutor e validação de CPF duplicado
- [ ] 6. Consulta de CEP válido e tratamento de CEP inexistente
- [ ] 7. Cadastro de animal e vínculo de microchip
- [ ] 8. Rejeição de microchip já utilizado

**Atendimento**
- [ ] 9. Registro de consulta e consulta ao histórico clínico
- [ ] 10. Registro de vacina e consulta às próximas doses

**Integração governamental**
- [ ] 11. Cadastro e atualização de animal na API governamental simulada
- [ ] 12. Envio obrigatório de vacina antirrábica
- [ ] 13. Ausência de comunicação para vacina não antirrábica
- [ ] 14. Indisponibilidade da API governamental e registro de pendência
- [ ] 15. Reenvio de comunicação pendente e confirmação posterior
- [ ] 16. Repetição de solicitação sem duplicidade no serviço externo


## 📚 Documentação

- [Requisitos e arquitetura](docs/requisitos/)
- [Diagrama ER e modelo relacional](docs/diagramas/)
- [Documentação dos endpoints (OpenAPI)](docs/api/)
- [Relatório de testes](docs/testes/)

## 👥 Equipe

| Nome | GitHub |
|---|---|
| _Felipe Martins_ | [@fox322](https://github.com/fox322) |
| _Stella Miranda_ | [@st3llami](https://github.com/st3llami) |
| _Yasmim Costa_ | [@YasmimCosta](https://github.com/YasmimCosta) |

**Professor:** _Fabio Gomes_

## ⚠️ Aviso

Este é um projeto **acadêmico**. A API governamental é **simulada** e **não** representa integração oficial com sistemas governamentais reais. Todos os dados utilizados são fictícios.

## 📄 Licença

Distribuído sob a licença MIT. Veja o arquivo [`LICENSE`](LICENSE).
