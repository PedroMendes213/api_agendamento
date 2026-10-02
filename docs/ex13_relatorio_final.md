# Relatório Final de Auditoria e Rastreabilidade

## 1. Objetivo

Este relatório consolida a auditoria final da API REST de agendamento de consultas médicas. A aplicação processa dados pessoais e informações de saúde, por isso foram avaliados autenticação, autorização, validação de entrada, persistência, exposição da especificação OpenAPI, headers HTTP, dependências e comportamento observado pelo OWASP ZAP.

## 2. Resultado executivo

A aplicação foi submetida a:

- testes funcionais automatizados;
- testes de segurança derivados do threat model;
- testes unitários com mocking;
- auditoria da especificação OpenAPI;
- análise estática com Bandit;
- análise de dependências com pip-audit;
- scan passivo com OWASP ZAP.

Resultados obtidos:

- 28 testes automatizados aprovados;
- 8 testes específicos do Exercício 13 aprovados;
- SAST aprovado;
- SCA aprovado;
- DAST com OWASP ZAP aprovado;
- Security Gate final aprovado.

O pipeline bloqueia a execução quando encontra falha em testes, vulnerabilidade High/Critical ou dependência sem classificação de risco verificável.

## 3. Rastreabilidade do threat model

### BOLA e controle de ownership

A ameaça identificada foi o acesso de um profissional à consulta pertencente a outro profissional ou paciente.

Categoria relacionada:

- OWASP API1:2023 — Broken Object Level Authorization;
- OWASP Top 10 A01:2021 — Broken Access Control.

Correções aplicadas:

- validação do usuário autenticado por JWT;
- verificação do profissional responsável pela consulta;
- funções centralizadas `garantir_leitura_consulta` e `garantir_gerenciamento_consulta`;
- restrição de listagem para o profissional autenticado;
- testes de acesso indevido com usuário profissional diferente;
- testes unitários com mocking da autorização.

Evidências:

- `tests/test_consultas.py`;
- `tests/test_exercicio13.py`;
- `ex13_01_testes_unitarios_mocking_openapi.png`;
- `ex13_02_suite_completa_28_passed.png`.

### Injeção e SQL Injection

A ameaça envolvia entrada de dados não validada e construção insegura de consultas.

Categoria relacionada:

- OWASP Top 10 A03:2021 — Injection.

Correções aplicadas:

- uso de SQLModel;
- queries construídas por expressões parametrizadas;
- ausência de concatenação de strings em consultas;
- validação de UUID, datas, enums e campos textuais;
- rejeição de campos extras com `extra="forbid"`;
- validação por regex para usernames e nomes de clientes;
- rejeição de datas malformadas.

### XSS armazenado

A aplicação possuía uma página HTML interna para consulta da agenda.

Categoria relacionada:

- OWASP Top 10 A03:2021 — Injection.

Correções aplicadas:

- autoescape habilitado no ambiente Jinja2;
- validação dos campos recebidos;
- renderização segura das observações;
- teste com payload `<script>alert('xss')</script>`.

O payload deixou de ser interpretado como código JavaScript e passou a ser exibido como texto escapado.

### Autenticação, JWT e MFA

A ameaça envolvia tokens inválidos, expirados, falsificação de claims e ausência de autenticação.

Categoria relacionada:

- OWASP Top 10 A07:2021 — Identification and Authentication Failures.

Correções aplicadas:

- autenticação OAuth2 Bearer;
- JWT assinado com algoritmo definido na configuração;
- expiração obrigatória dos tokens;
- rejeição de tokens malformados ou expirados;
- validação do tipo de token;
- verificação de role;
- bcrypt para armazenamento de senhas;
- MFA obrigatório para administradores;
- segredo JWT carregado pelo `.env`, sem credencial real no repositório.

### Força bruta no login

A ameaça envolvia tentativas repetidas de autenticação.

Categoria relacionada:

- OWASP Top 10 A07:2021 — Identification and Authentication Failures.

Correção aplicada:

- rate limiting específico para o endpoint de login;
- resposta HTTP 429 após exceder o limite;
- parâmetros configuráveis pelo `BaseSettings`.

### CORS e configuração HTTP

A ameaça envolvia origens não autorizadas e ausência de headers defensivos.

Categoria relacionada:

- OWASP Top 10 A05:2021 — Security Misconfiguration.

Correções aplicadas:

- CORS configurado com allowlist explícita;
- rejeição de origens desconhecidas;
- `Strict-Transport-Security`;
- `X-Frame-Options: DENY`;
- `X-Content-Type-Options: nosniff`;
- headers contra armazenamento de respostas sensíveis em cache.

### Dependências vulneráveis

A análise inicial identificou versões vulneráveis de `python-multipart`, `PyJWT`, `pytest` e `Starlette`.

Categoria relacionada:

- OWASP Top 10 A06:2021 — Vulnerable and Outdated Components.

Correções aplicadas:

- atualização das dependências no `requirements.txt`;
- execução do `pip-audit`;
- bloqueio automático pelo Security Gate quando a dependência possui risco High/Critical ou classificação não verificável.

## 4. Auditoria da especificação OpenAPI

A especificação OpenAPI foi auditada automaticamente pelos testes do Exercício 13.

Foram confirmados:

- existência do esquema OAuth2;
- `tokenUrl` configurado como `/auth/token`;
- presença do escopo `agenda:horarios`;
- proteção das rotas de consultas;
- proteção da página de agenda;
- ausência dos campos internos `senha_hash` e `client_secret_hash`;
- ausência de credenciais sensíveis na documentação pública.

## 5. Resultado do OWASP ZAP

Foi executado um scan passivo com OWASP ZAP 2.17.0 contra a aplicação em execução.

Resultado final:

- High: 0;
- Medium: 0;
- Low: 0;
- Informational: 1;
- False Positives: 0.

O alerta informativo encontrado foi:

- Nome: `Non-Storable Content`;
- Plugin: 10049;
- CWE: 524;
- WASC: 13;
- URLs observadas: `/` e `/robots.txt`.

O alerta indica que as respostas não são armazenáveis por componentes de cache. Esse comportamento é esperado e desejável para uma API que processa informações pessoais e de saúde. A configuração foi obtida com:

- `Cache-Control: no-store, no-cache, must-revalidate, private`;
- `Pragma: no-cache`;
- `Expires: 0`.

Não foram encontrados alertas High, Medium ou Low.

## 6. Critério de aprovação

O Security Gate foi configurado para bloquear quando:

1. qualquer teste automatizado falhar;
2. o Bandit encontrar vulnerabilidade High;
3. o pip-audit identificar dependência vulnerável;
4. uma dependência tiver vulnerabilidade sem score verificável;
5. o OWASP ZAP encontrar alerta High ou Critical;
6. qualquer etapa obrigatória do pipeline terminar com erro.

O limite de severidade foi definido em CVSS 7.0, pois vulnerabilidades nesse nível podem causar exposição ou alteração de dados clínicos.

## 7. Riscos residuais

O scan passivo não valida completamente controles externos à aplicação, como:

- configuração definitiva de TLS no ambiente de produção;
- proteção e rotação das credenciais de produção;
- criptografia de backups;
- retenção e controle de acesso aos logs;
- monitoramento contínuo de novas vulnerabilidades.

A decisão é autorizar a liberação de forma condicional. A aplicação está aprovada tecnicamente pelo pipeline, mas o deploy somente deve ocorrer com HTTPS obrigatório, segredo JWT armazenado em mecanismo seguro, backups protegidos e controle de acesso operacional.

Se essas condições de infraestrutura não forem atendidas, a liberação deve ser bloqueada.

## 8. Conclusão

A API apresentou comportamento aprovado nos testes funcionais e de segurança. Os controles de autenticação, autorização, ownership, validação, persistência parametrizada, CORS, headers, rate limiting, MFA, escopos M2M e auditoria OpenAPI foram implementados e testados.

O OWASP ZAP não encontrou vulnerabilidades High, Medium ou Low. O Security Gate final foi aprovado, permitindo considerar a aplicação pronta para a próxima etapa, condicionada aos controles operacionais descritos nos riscos residuais.