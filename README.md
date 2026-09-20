# HospitalitySync

HospitalitySync é um sistema fictício de gestão hoteleira desenvolvido como projeto de portfólio para demonstrar engenharia de software, modelagem relacional, APIs, autenticação, regras de negócio e interfaces operacionais integradas.

O projeto utiliza uma única aplicação FastAPI e um único banco PostgreSQL para atender três ambientes físicos: recepção, dispositivos instalados nos quartos e cozinha.

## Objetivo

O MVP cobre o fluxo operacional essencial de um hotel:

- cadastro de hóspedes e reservas;
- controle de disponibilidade e conflitos de datas;
- check-in, hospedagem e check-out;
- identificação segura dos dispositivos dos quartos;
- solicitações de limpeza, manutenção, ajuda e reclamações;
- cardápio, pedidos de comida e operação da cozinha;
- atualizações em tempo real entre quarto, recepção e cozinha.

O sistema não contém dados demonstrativos automáticos. Tudo o que aparece nas interfaces é obtido do banco de dados.

## Tecnologias

- Python 3.11+
- FastAPI
- PostgreSQL — testado com PostgreSQL 18.6
- SQLAlchemy 2
- Alembic
- Pydantic 2
- Psycopg 3
- Jinja2
- HTML, CSS e JavaScript
- WebSockets
- Pytest e HTTPX
- Argon2 por meio do `pwdlib`

## Arquitetura

O backend é um monólito organizado em camadas:

```text
HTTP / WebSocket
       ↓
Routes — transporte, autenticação, entrada e resposta
       ↓
Services — regras de negócio e transições de estado
       ↓
Repositories — consultas e persistência
       ↓
SQLAlchemy / PostgreSQL
```

Schemas Pydantic definem os contratos de entrada e saída. Templates não consultam o banco e os routers não contêm consultas SQLAlchemy. Os Models são a fonte de verdade da persistência e o Alembic mantém o schema versionado.

### Interfaces

```text
Backend e banco centralizados
├── /reception  Recepção e operação do hotel
├── /guest      Tablet vinculado a um quarto
└── /kitchen    Operação da cozinha
```

#### Reception

Acesso exclusivo de usuários com role `RECEPTION`. Inclui dashboard operacional, reservas, hóspedes, check-in/check-out, dispositivos e solicitações dos quartos.

#### Guest / Room

Cada dispositivo é provisionado pela recepção e recebe uma credencial aleatória. O banco armazena somente o hash da credencial. O backend determina o quarto a partir do dispositivo autenticado; as operações do hóspede não aceitam um `room_id` escolhido pelo cliente.

#### Kitchen

Acesso exclusivo de usuários com role `KITCHEN`. Permite administrar o cardápio, visualizar pedidos e avançar o fluxo de preparação.

## Funcionalidades

### Recepção

- dashboard com dados reais do banco;
- criação, edição, listagem, filtros e cancelamento lógico de reservas;
- prevenção de reservas sobrepostas no Service Layer e no PostgreSQL;
- cadastro, edição e desativação de hóspedes;
- check-in e check-out transacionais;
- atualização do estado dos quartos;
- provisionamento e revogação de dispositivos;
- acompanhamento de serviços solicitados pelos quartos.

### Quartos

- pareamento temporário do tablet com um quarto;
- visualização da hospedagem ativa;
- solicitação de limpeza, manutenção, ajuda e registro de reclamações;
- histórico de solicitações da hospedagem atual;
- cardápio e pedidos de comida;
- acompanhamento dos pedidos.

### Cozinha

- autenticação específica por role;
- criação, edição e disponibilidade de itens do cardápio;
- fila e histórico de pedidos;
- fluxo `RECEIVED → PREPARING → READY → DELIVERED`;
- preço do item preservado no momento do pedido.

## Estrutura de pastas

```text
HospitalitySync/
├── alembic/                 # Ambiente e versões das migrations
├── app/
│   ├── core/                # Configuração e funções de segurança
│   ├── database/            # Base SQLAlchemy, engine e sessões
│   ├── models/              # Models e relacionamentos
│   ├── repositories/        # Acesso ao banco
│   ├── routers/             # HTTP e WebSockets
│   ├── schemas/             # Contratos Pydantic
│   ├── services/            # Regras de negócio
│   ├── static/              # CSS e JavaScript
│   ├── templates/           # Interfaces Jinja2
│   ├── main.py              # Application factory
│   └── realtime.py          # Hub WebSocket do MVP
├── tests/                   # Testes automatizados
├── .env.example             # Exemplo sem credenciais reais
├── alembic.ini
├── requirements.txt
└── requirements-dev.txt
```

## Instalação local

### 1. Clonar e criar o ambiente virtual

```bash
git clone <URL_DO_REPOSITORIO>
cd HospitalitySync
python -m venv .venv
```

Ativação no Linux/macOS:

```bash
source .venv/bin/activate
```

Ativação no PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar dependências

Para executar a aplicação:

```bash
python -m pip install -r requirements.txt
```

Para desenvolvimento e testes:

```bash
python -m pip install -r requirements-dev.txt
```

## PostgreSQL

Crie um banco vazio e um usuário com acesso a ele. Um exemplo usando as ferramentas do PostgreSQL é:

```bash
createdb hospitalitysync
```

O usuário utilizado pela aplicação precisa conseguir criar tabelas, índices, constraints e a extensão `btree_gist`, usada pela exclusion constraint que impede reservas sobrepostas. Em ambientes gerenciados, a extensão pode precisar ser habilitada previamente pelo administrador.

Não crie tabelas manualmente. A estrutura é gerenciada pelo Alembic.

## Variáveis de ambiente

Copie o exemplo:

```bash
cp .env.example .env
```

No PowerShell:

```powershell
Copy-Item .env.example .env
```

Variáveis necessárias:

| Variável | Finalidade |
| --- | --- |
| `DATABASE_URL` | URL SQLAlchemy do PostgreSQL usando Psycopg |
| `SESSION_SECRET_KEY` | Assinatura criptográfica da sessão; mínimo de 32 caracteres |
| `SESSION_COOKIE_SECURE` | Use `true` com HTTPS; somente desenvolvimento HTTP deve usar `false` |
| `SESSION_MAX_AGE_SECONDS` | Duração da sessão dos funcionários |
| `DEVICE_COOKIE_MAX_AGE_SECONDS` | Duração da credencial local do dispositivo do quarto |

Formato esperado para a conexão:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
```

Gere uma chave de sessão forte:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Nunca versione o `.env`. Ele já está listado no `.gitignore`; somente `.env.example`, sem valores reais, deve entrar no repositório.

A aplicação lê variáveis do ambiente do processo. O arquivo `.env` não é carregado diretamente pelo módulo de configuração. Durante o desenvolvimento, o Uvicorn pode carregá-lo com `--env-file .env`; para comandos Alembic, exporte as variáveis no shell antes da execução. Em produção, prefira as variáveis/secrets fornecidos pela plataforma.

## Migrations

Exporte as variáveis de ambiente no shell e execute:

```bash
python -m alembic upgrade head
```

Verifique a revisão atual:

```bash
python -m alembic current
```

Confirme que os Models e migrations estão sincronizados:

```bash
python -m alembic check
```

Desfaça somente a última migration quando realmente necessário:

```bash
python -m alembic downgrade -1
```

## Usuários operacionais

O projeto não inclui usuários ou senhas padrão. Antes do primeiro acesso, crie usuários `RECEPTION` e `KITCHEN` por um procedimento administrativo controlado, armazenando no campo `password_hash` apenas um hash Argon2 produzido pelo `PasswordHasher` da aplicação.

Não coloque senhas em scripts versionados, comandos salvos ou migrations. Para um ambiente real, o bootstrap deve ser feito por uma ferramenta administrativa segura ou por um processo de deploy que leia a senha de um secret manager.

## Executando a aplicação

O projeto utiliza uma application factory:

```bash
python -m uvicorn app.main:create_app --factory --env-file .env --reload
```

Interfaces principais:

- `http://localhost:8000/reception`
- `http://localhost:8000/guest/setup`
- `http://localhost:8000/kitchen/login`
- documentação da API: `http://localhost:8000/docs`

O login da recepção é realizado por `POST /auth/login`; o login da cozinha, por `POST /auth/kitchen/login`. As áreas operacionais continuam protegidas mesmo que alguém tente acessar diretamente as URLs.

## Testes

Execute a suíte completa:

```bash
python -m pytest -q
```

Os testes usam SQLite em memória com uma adaptação controlada dos tipos PostgreSQL. Eles não dependem do banco local, de credenciais reais, de rede ou de dados externos. As constraints específicas do PostgreSQL também são verificadas pela metadata e pela sincronização do Alembic com o banco real.

Na auditoria para publicação, a suíte apresentou:

```text
76 passed
Cobertura de app: 88%
```

## Fluxos principais

### Reserva e hospedagem

```text
Recepção cadastra/seleciona hóspede e quarto
→ Service valida datas, capacidade e disponibilidade
→ PostgreSQL também impede sobreposição por exclusion constraint
→ reserva CONFIRMED
→ check-in registra actual_check_in_at e quarto OCCUPIED
→ hospedagem ativa usa o estado CHECKED_IN da reserva
→ check-out registra actual_check_out_at e quarto CLEANING
```

A modelagem aprovada representa a hospedagem na própria `Reservation`; não existe uma entidade `Stay` duplicada.

### Pedido de comida

```text
Dispositivo autenticado identifica o quarto
→ backend encontra a hospedagem CHECKED_IN
→ hóspede escolhe itens disponíveis
→ pedido guarda quantidade e preço unitário daquele momento
→ cozinha recebe evento WebSocket
→ RECEIVED → PREPARING → READY → DELIVERED
→ cada atualização é enviada ao dispositivo do quarto correto
```

## WebSockets

Existem canais autenticados e separados para recepção, cozinha e quartos. Os eventos transportam apenas identificadores e estados mínimos; os clientes recuperam os dados completos pelas rotas HTTP já autorizadas.

O hub atual mantém conexões em memória e é apropriado para uma única instância do MVP. Para executar múltiplos workers ou réplicas, substitua-o por um backplane compartilhado, como Redis Pub/Sub, antes de habilitar escalabilidade horizontal.

## Segurança

- senhas com Argon2 e nunca retornadas pela API;
- sessão assinada em cookie `HttpOnly`;
- cookies seguros por padrão em produção;
- credenciais de dispositivos armazenadas somente em hash;
- autorização por role aplicada no backend;
- isolamento do quarto derivado da credencial do dispositivo;
- proteção de Origin para mutações e WebSockets;
- CSP, proteção contra framing, `nosniff`, Referrer Policy e HSTS com cookies seguros;
- secrets fornecidos somente por variáveis de ambiente;
- respostas não incluem `password_hash`, documentos de hóspedes no dashboard ou credenciais internas.

## Desenvolvimento local e produção

Em desenvolvimento HTTP local, defina `SESSION_COOKIE_SECURE=false`. Em produção:

- use HTTPS e mantenha `SESSION_COOKIE_SECURE=true`;
- gere um `SESSION_SECRET_KEY` exclusivo e armazene-o em um secret manager;
- execute `alembic upgrade head` como etapa controlada do deploy;
- não use `--reload`;
- configure corretamente os headers do proxy reverso para que esquema e host sejam preservados;
- restrinja o usuário do banco e o acesso de rede ao PostgreSQL;
- adicione observabilidade, backups e rotação de secrets conforme o ambiente;
- use apenas um worker enquanto o hub WebSocket for mantido em memória.

## Estado do projeto

O repositório representa um MVP de portfólio funcional e testado. Funcionalidades futuras devem preservar as camadas existentes e ser acompanhadas de Models/migrations apenas quando o schema atual não for suficiente.
