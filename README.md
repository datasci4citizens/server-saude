![Django](https://img.shields.io/badge/backend-django-green)
![PostgreSQL](https://img.shields.io/badge/db-postgres-blue)
![OMOP](https://img.shields.io/badge/model-omop-orange)


# 🧠 SAÚDE! — Sistema de Apoio à Saúde Mental no SUS

> Um app mobile e sistema web pensados para facilitar o acompanhamento de pessoas com sofrimento psíquico, integrando pacientes, ACS, psicólogos e psiquiatras de forma humanizada e extensível.

---

## 🚀 Visão Geral

O SAÚDE! é um sistema em constante evolução que:

- Registra hábitos, sintomas e sentimentos de pacientes
- Permite a personalização do acompanhamento
- Compartilha dados com profissionais apenas quando o paciente autoriza
- Usa o modelo de dados [OMOP](https://www.ohdsi.org/data-standardization/the-common-data-model/) para garantir extensibilidade e interoperabilidade
- Está sendo desenvolvido com foco na **RAPS (Rede de Atenção Psicossocial)**

---

## 🧩 Tecnologias

- **Backend**: Django + Django REST Framework
- **Banco de dados**: PostgreSQL (modelo OMOP adaptado)
- **Mobile App**: React + Capacitor (em desenvolvimento)
- **Infra**: Docker para banco de dados

---

## 🔗 Links úteis

| Recurso | Link |
|--------|------|
| 📐 Diagrama do Banco de Dados (OMOP) | [dbdocs.io/saude_mental_database](https://dbdocs.io/Andr%C3%A9%20Amadeu%20Satorres/saude_mental_database) |
| 🎨 Protótipos Figma | [Figma do frontend](https://www.figma.com/design/GNpltZCrw4r6nZ74BG1a0D/SAUDE-TELAS?node-id=50-209&p=f&t=2mutAsoFPhOtujGn-0) |
| 📋 Quadro de tarefas (Trello) | [Trello do projeto SAÚDE!](https://trello.com/b/zcAUxXKt/saude) |

---

## 📦 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/saude-backend.git
cd saude-backend
```

### 2. Crie o ambiente virtual

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Suba o banco PostgreSQL com Docker

```bash
docker-compose up -d
```

### 5. Carregue o banco e os dados iniciais

```bash
psql -U saude_user -d saude_db -f ./scripts/saude.sql
python manage.py loaddata initial_fixtures.json
```

### 6. Rode o servidor

```bash
python manage.py runserver
```

---

## 📌 Endpoints de exemplo

| Endpoint | Descrição |
|----------|-----------|
| `/api/concepts/` | Lista de conceitos padrão (mood, hábito, etc) |
| `/api/observations/` | Registros dos pacientes |
| `/api/drugexposure/` | Controle de medicação |
| `/api/person/` | Perfis de pacientes |
| `/api/provider/` | Profissionais de saúde vinculados |

---

## ✨ Contribuindo

1. Crie uma branch com sua feature ou correção
2. Faça commit com mensagens claras
3. Abra um Pull Request aqui no GitHub

### Pre-commit hooks (formatação automática)
Usamos o [pre-commit](https://pre-commit.com/) para manter o código formatado e limpo automaticamente antes de cada commit.

✅ Setup inicial:
```bash
pip install pre-commit
pre-commit install
```

Isso instala os hooks para rodar automaticamente.

Hooks incluídos:
- black: formatação padrão para Python
- isort: ordenação de imports
- flake8: boas práticas e erros comuns
- end-of-file-fixer: insere \n no final dos arquivos
- trailing-whitespace: remove espaços extras

O arquivo .pre-commit-config.yaml já está incluído na raiz do projeto.

### 🌿 Formato de branches

Use o padrão:

```md
tipo/SAU-ticket/nome-descritivo
```

Onde "ticket" é o número do ticket no trello associado com essa mudança.

#### Exemplos:

- `feat/SAU-7/observation-endpoint`
- `fix/SAU-7/concept-foreign-key-error`
- `hotfix/SAU-5/production-crash`
- `docs/SAU-3/readme-ajustes`

Tipos recomendados:
- `feat/` → nova funcionalidade
- `fix/` → correções de bugs
- `refactor/` → mudanças internas sem mudar comportamento
- `hotfix/` → correções urgentes
- `docs/` → documentação

---

### 🚀 Formato dos Merge Requests

> Evite nomes genéricos como "Update code" ou "final version"

Use:

```
- feat(SAU-7): Adiciona endpoint de observações
- fix(SAU-5): Corrige constraint de concept
- refactor(SAU-3): Limpa models e serializers
- docs(SAU-45): Adiciona instruções de setup no README
```

E sempre adicione:

- O **contexto** da mudança
- Se afeta algo que precisa ser testado
- Link para o card no Trello (se aplicável)
