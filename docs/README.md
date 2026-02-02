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

|              Recurso                 |              Link                |
|--------------------------------------|----------------------------------|
| 📐 Diagrama do Banco de Dados (OMOP) | [dbdocs.io/saude-database](https://dbdocs.io/André%20Amadeu%20Satorres/SAUDE-DB?view=relationships)        |
| 🎨 Protótipos Figma                  | [Figma do frontend](https://www.figma.com/design/GNpltZCrw4r6nZ74BG1a0D/)               |

---

## 📦 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/datasci4citizens/server-saude
```
### 2. Variáveis de ambiente:
- Na raiz:
   Copie `.env.model` para `.env` e ajuste as variáveis:
      SECRET_KEY (sua chave secreta, é utilizada para manter o login no app/site, guardar tokens, entre outras coisas)
      VITE_GOOGLE_CLIENT_ID e VITE_GOOGLE_CLIENT_SECRET (permitem fazer o login através da API do Google)

- Na pasta 'docker/' 

   Copie `docker-compose-model.yml` para `docker-compose.yml` e ajuste as variaveis:
      volumes - device (pasta onde será guardado o banco de dados local)

### 3. Crie o ambiente virtual
(no diretorio server-saude/citizens_project/)

```bash

# é importante utilizar a versão 3.13, pois algumas dependencias não tem suporte para versoes mais novas.
python3.13 -m venv .venv  # apenas na primera vez


#linux
source .venv/bin/activate 


#windows
.\.venv\Scripts\Activate.ps1
```


### 4. Instale as dependências no ambiente virtual (apenas primeiro acesso)

```bash
pip install -r requirements.txt
```

### 5. Suba o banco PostgreSQL com Docker

```bash
cd ../docker
docker compose up -d     #linux pode precisar de SUDO
```

### 6. Faça as migrações iniciais
```bash
cd ../citizens_project
python manage.py makemigrations
python manage.py migrate

### 7. Rode as Seeds

```bash
python manage.py seed_all
```

### 8. Rode o servidor

```bash
python manage.py runserver
```

---

## 📌 Endpoints de exemplo

|      Endpoint       |                  Descrição                    |
|---------------------|-----------------------------------------------|
| `/api/concepts/`    | Lista de conceitos padrão (mood, hábito, etc) |
| `/api/observations/`| Registros dos pacientes                       |
| `/api/drugexposure/`| Controle de medicação                         |
| `/api/person/`      | Perfis de pacientes                           |
| `/api/provider/`    | Profissionais de saúde vinculados             |

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
tipo/ticket/nome-descritivo
```

Onde "ticket" é o número do ticket no github issues associado com essa mudança.

#### Exemplos:

- `feat/7/observation-endpoint`
- `fix/7/concept-foreign-key-error`
- `hotfix/5/production-crash`
- `docs/3/readme-ajustes`

Tipos:
- `feat/` → nova funcionalidade
- `fix/` → correções de bugs
- `refactor/` → mudanças internas sem mudar comportamento
- `hotfix/` → correções urgentes
- `docs/` → documentação

---

### 🚀 Formato dos Pull Requests

> Evite nomes genéricos como "Update code" ou "final version"

Use:

```
- feat(7): Adiciona endpoint de observações
- fix(5): Corrige constraint de concept
- refactor(3): Limpa models e serializers
- docs(45): Adiciona instruções de setup no README
```

E sempre adicione:

- O **contexto** da mudança
- Se afeta algo que precisa ser testado
- Link para o issue no Github

---

### 🛠️ Mudanças no Banco de Dados

Sempre que houver alterações no banco de dados, siga este fluxo:

1. **Atualizar o `models.py`**

   - Faça as mudanças necessárias nas classes Django (`./citizens_project/app_saude/models.py`).

2. **Atualizar o `.dbml`**

   - Atualize o arquivo DBML correspondente na pasta `docker/` (`docker/saude.dbml`) para refletir as mudanças feitas no `models.py`.
   - O DBML é usado para gerar a documentação visual do banco.

3. **Subir o banco de dados local**

   - Suba o PostgreSQL usando Docker:
   
   ```bash
      cd docker
      docker compose up -d
   ```

4. **Gerar e aplicar migrações**

   - Rode o `makemigrations` e `migrate` para aplicar as mudanças no Postgres:
   
     ```bash
     cd citizens_project
     python manage.py makemigrations
     python manage.py migrate
     ```

   - Se o Django pedir valor default para novos campos, forneça quando aplicável.

5. **Atualizar a documentação DBML**

   - Após tudo estar correto, atualize a documentação no [dbdocs.io](https://dbdocs.io/):

     ```bash
     dbdocs login    # apenas na primeira vez
     dbdocs build ./docker/saude.dbml
     ```

   - Isso irá reconstruir e publicar a documentação atualizada.

---

#### 📋 Observações Importantes
- Sempre mantenha o **`models.py`** e o **`saude.dbml`** **sincronizados**.
- O arquivo `.dbdocs.yml` controla o projeto que será publicado no dbdocs.io.
