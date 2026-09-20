# Entrega da camada visual

Endereço local: http://localhost:8000.

## Componentes

- Landing page com identidade azul-petróleo, diagrama SVG/CSS dos ambientes, hub de acesso e chamadas para ação.
- Login compartilhado da recepção e cozinha, com mostrar/ocultar senha, feedback genérico e proteção contra submissão repetida.
- Navegação compartilhada da recepção, recolhível e adaptada a telas menores.
- Dashboard com indicadores reais, quartos em cards, reservas recentes e últimas solicitações.
- Serviços com filtros, horários e ações existentes; não há prioridade fictícia.
- Cozinha em quatro colunas, com pedidos e cardápio reais.
- Quarto com ações grandes, informações da estadia, solicitações e progresso dos pedidos.
- Toasts, estados vazios, carregamento, feedback de atualização e indicador de conexão real.
- Atualizações parciais a partir dos WebSockets existentes, preservando formulários em preenchimento.
- Página de acesso necessário para visitantes sem autorização, preservando 401/403 e respostas JSON.
- Foco visível, labels, link para pular navegação, suporte a teclado e movimento reduzido.

## Arquivos criados nesta etapa

```text
app/static/css/base.css
app/static/css/landing.css
app/static/css/product.css
app/static/js/base.js
app/static/js/login.js
app/templates/base.html
app/templates/landing.html
app/templates/login.html
app/templates/access-required.html
app/templates/components/icons.html
app/templates/components/reception-sidebar.html
app/templates/reception/login.html
tests/frontend.test.cjs
docs/frontend.md
```

## Arquivos modificados nesta etapa

```text
app/main.py
app/routers/reception.py
app/static/js/reception.js
app/static/js/reception-dashboard.js
app/static/js/reception-services.js
app/static/js/guest-services.js
app/static/js/guest-food.js
app/static/js/kitchen.js
app/templates/reception/dashboard.html
app/templates/reception/reservations/list.html
app/templates/reception/reservations/form.html
app/templates/reception/guests/list.html
app/templates/reception/guests/form.html
app/templates/reception/stays/operations.html
app/templates/reception/devices/list.html
app/templates/reception/services/list.html
app/templates/guest/dashboard.html
app/templates/guest/food.html
app/templates/guest/setup.html
app/templates/kitchen/dashboard.html
app/templates/kitchen/login.html
tests/test_security.py
tests/test_food_orders.py
README.md
```

Removido: `app/static/js/kitchen-login.js`, substituído pelo cliente de login compartilhado. O arquivo era exclusivamente frontend; os endpoints de autenticação permanecem os mesmos.

Dockerfile, Compose, `.dockerignore` e `.env.example` já tinham alterações anteriores à tarefa; não foram modificados nesta etapa.

## Integração com backend

`GET /` passou a renderizar a landing page. A única nova rota é `GET /reception/login`, que serve um formulário público e envia credenciais para o `POST /auth/login` existente.

O router da recepção passa ao dashboard as oito solicitações mais recentes usando `ServiceRequests.list_for_reception()`, sem consultas no template e sem modificar Services ou Repositories. Esse método existente carrega a lista antes de recortá-la; paginação no banco é uma melhoria futura para volumes maiores.

O tratamento visual de 401/403 se aplica a requisições com `Accept: text/html` nas três áreas. Status e regras de autorização não mudam; requisições JSON mantêm o contrato existente.

Models, migrations, Services, Repositories, schemas, autenticação, RBAC e servidor WebSocket não foram alterados. Nenhuma credencial foi adicionada ao frontend e nenhum dado foi inserido no banco.

## Verificação executada

| Verificação | Resultado |
| --- | --- |
| `python -m pytest -q` | 84 passaram; um aviso de depreciação do Starlette/AnyIO |
| `node --test tests/frontend.test.cjs` | 5 passaram |
| `node --check` em todos os scripts | Sem erros de sintaxe |
| `python -m compileall -q .` | Sucesso |
| `git diff --check` | Sucesso |
| `docker compose config --quiet` | Sucesso; saída resolvida omitida para não divulgar secrets |
| `docker compose up -d --build` | Build e inicialização concluídos |
| `docker compose ps` | App ativo, PostgreSQL healthy |
| `docker compose exec -T app python -m alembic check` | No new upgrade operations detected |
| `docker compose exec -T app python -m alembic current` | 14dcc1cd477e (head) |
| HTTP `/`, `/reception/login`, `/kitchen/login`, `/guest/setup`, `/docs`, `/openapi.json` | 200 |
| HTTP sem credenciais `/reception`, `/kitchen`, `/guest` | 401, conforme esperado |

Os testes exercitam login/logout, separação de roles/quartos, renderização com dados, fluxo de pedidos, notificações WebSocket e falhas de rede do cliente. Os dados dos testes são isolados em SQLite em memória e não são carregados no PostgreSQL Docker.

## Limites conhecidos

Não foi possível inspecionar visualmente as telas em navegador nesta sessão: não havia navegador conectado, e o serviço de automação do computador estava indisponível. Portanto, as verificações HTTP, de templates e de JavaScript não equivalem a uma validação visual de desktop/tablet/celular. Essa conferência permanece pendente.

O feed da recepção representa solicitações reais persistidas. O backend não transmite eventos de toda a operação para a recepção; indicadores de pedidos/check-in/check-out também podem ser atualizados manualmente. Nenhum evento ou prioridade inexistente foi simulado. O hub público informa requisitos de acesso, não a disponibilidade online dos dispositivos.

O banco pode estar vazio: a interface apresenta estados vazios e exige contas/dispositivos previamente provisionados pelos mecanismos existentes. Não existem credenciais de demonstração.

Nenhum commit ou push foi realizado.
