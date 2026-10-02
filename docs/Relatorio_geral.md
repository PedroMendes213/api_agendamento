# Relatório Técnico Final — API de Agendamento de Consultas

## 1. Apresentação

Este projeto consistiu no desenvolvimento seguro de uma API REST para uma rede de clínicas médicas. A aplicação permite o gerenciamento de consultas, disponibiliza uma página HTML interna para a recepção e possui uma integração máquina-a-máquina com um laboratório parceiro.

Como o sistema processa identificadores de pacientes, profissionais, horários e observações de consultas, a segurança foi considerada desde a modelagem até o pipeline final de entrega.

A aplicação foi desenvolvida com:

- FastAPI;
- APIRouter;
- Pydantic;
- SQLModel;
- SQLite no ambiente local;
- JWT;
- OAuth2;
- bcrypt;
- Jinja2;
- pytest;
- Bandit;
- pip-audit;
- OWASP ZAP;
- GitHub Actions.

O vídeo demonstrativo deve ser incluído neste relatório:

Vídeo no YouTube: [INSERIR LINK DO VÍDEO NÃO LISTADO]

---

## 2. Exercício 1 — Fundação da API

Foi criado um ambiente Python isolado utilizando `venv`, evitando que as dependências do projeto interferissem em outros projetos do computador.

A aplicação foi organizada em módulos:

- `app/routes`: endpoints da aplicação;
- `app/models.py`: modelos SQLModel e Pydantic;
- `app/database.py`: conexão e sessões do banco;
- `app/auth.py`: autenticação e autorização;
- `app/security.py`: controles contra abuso;
- `app/templates`: página HTML da agenda;
- `tests`: testes automatizados.

Foi implementado o recurso de consultas utilizando `APIRouter`, incluindo operações de criação, listagem, busca, atualização e exclusão.

A persistência inicial foi realizada com SQLite por meio do SQLModel. Também foi criado o primeiro teste automatizado com pytest, validando o caminho de sucesso da criação e listagem de uma consulta.

---

## 3. Exercício 2 — Agenda HTML e apresentação segura

Foi criada a página HTML interna utilizada pela recepção para consultar a agenda do dia.

A rota `GET /agenda` recebe uma data validada e consulta as consultas daquele dia. O resultado é renderizado com Jinja2 por meio do template `consultas.html`.

Como o campo de observações pode conter conteúdo fornecido por usuários, foi habilitado o escape automático do Jinja2.

Foi criado um teste com o payload:

`<script>alert('xss')</script>`

O teste comprovou que o conteúdo não é executado como JavaScript e passa a ser exibido de forma escapada no HTML.

---

## 4. Exercício 3 — Modelagem inicial de segurança

Foi realizada a análise inicial da aplicação utilizando a tríade CIA:

- confidencialidade;
- integridade;
- disponibilidade.

Foram identificados os principais ativos:

- dados de pacientes;
- dados de profissionais;
- registros de consultas;
- agenda da clínica;
- configurações da aplicação;
- credenciais e tokens;
- disponibilidade do serviço.

Também foram documentados os fluxos entre:

- frontend e API;
- recepção e API;
- laboratório e API;
- API e banco de dados.

A análise foi relacionada a referências como OWASP, NIST SSDF e MITRE ATT&CK.

Os riscos iniciais identificados incluíram:

- acesso sem autenticação;
- ausência de ownership;
- XSS;
- SQL Injection;
- exposição de campos internos;
- força bruta;
- credenciais expostas;
- excesso de privilégios na integração externa;
- acesso direto ao banco local.

---

## 5. Exercício 4 — Threat model com STRIDE

Foi elaborado o modelo de ameaças utilizando o framework STRIDE.

Foram analisadas as ameaças de:

- Spoofing;
- Tampering;
- Repudiation;
- Information Disclosure;
- Denial of Service;
- Elevation of Privilege.

As principais fronteiras de confiança identificadas foram:

1. clientes externos e API;
2. API e camada interna;
3. aplicação e banco de dados;
4. API e laboratório parceiro;
5. API e navegador da recepção.

O risco mais grave identificado foi o BOLA, pois um usuário autenticado poderia tentar alterar o identificador de uma consulta para acessar o registro de outra pessoa.

Também foram identificados riscos de:

- autenticação insuficiente;
- ausência de autorização por objeto;
- XSS armazenado;
- SQL Injection;
- força bruta;
- tokens M2M com privilégios excessivos;
- CORS permissivo;
- exposição da documentação;
- ausência de rate limiting;
- acesso direto ao arquivo SQLite.

---

## 6. Exercício 5 — Arquitetura e vetores de ataque

A arquitetura foi dividida em cinco partições:

- clientes externos;
- camada HTTP e API;
- validação, regras e segurança;
- persistência;
- operação e configuração.

Os vetores de ataque foram classificados em três grupos.

### Design

Foram analisados:

- BOLA;
- exposição excessiva de dados;
- endpoints com responsabilidades amplas;
- integração externa com privilégios excessivos;
- ausência de menor privilégio.

### Implementação

Foram analisados:

- validação insuficiente;
- SQL Injection;
- XSS;
- mass assignment;
- bypass de autenticação;
- informações excessivas em mensagens de erro;
- payloads muito grandes.

### Infraestrutura

Foram analisados:

- comunicação sem HTTPS;
- exposição da documentação;
- CORS permissivo;
- ausência de headers;
- ausência de rate limiting;
- banco local sem estratégia operacional;
- ausência de monitoramento e backup.

Essa análise serviu de base para os testes e correções realizados nos exercícios seguintes.

---

## 7. Exercício 6 — Autenticação, autorização e ownership

Foi implementada autenticação baseada em OAuth2 Bearer e JWT.

As senhas são armazenadas utilizando bcrypt, nunca em texto puro.

Os tokens passaram a conter claims como:

- `sub`;
- `role`;
- `profissional_id`;
- `mfa`;
- `token_type`;
- `iat`;
- `exp`.

Foi implementado controle de acesso baseado em papéis:

- recepcionista;
- profissional;
- administrador.

Também foi criado o bootstrap do administrador com MFA obrigatório.

O controle de ownership foi centralizado em funções específicas, como:

- `garantir_leitura_consulta`;
- `garantir_gerenciamento_consulta`;
- `garantir_profissional_da_consulta`.

Assim, um profissional somente pode consultar ou alterar consultas relacionadas ao seu próprio identificador profissional. Administradores possuem permissões administrativas, enquanto recepcionistas possuem permissões de consulta compatíveis com sua função.

Foram criados testes para:

- rejeitar acesso sem JWT;
- rejeitar token inválido;
- bloquear usuário sem papel administrativo;
- impedir profissional de acessar consulta de outro profissional;
- validar o controle de ownership.

---

## 8. Exercício 7 — OAuth2 e integração M2M

Para o laboratório parceiro foi implementado o fluxo OAuth2 `client_credentials`, adequado para comunicação máquina-a-máquina.

Cada cliente M2M possui:

- `client_id`;
- segredo armazenado com hash;
- status ativo ou inativo;
- escopos contratados.

O token do laboratório contém claims específicas:

- `token_type: m2m`;
- `client_type: laboratorio`;
- `grant_type: client_credentials`;
- `client_id`;
- `scope`.

Foi definido o escopo:

`agenda:horarios`

Esse escopo permite somente a consulta de horários disponíveis.

Um token de profissional não pode utilizar o endpoint exclusivo do laboratório. O laboratório também não pode acessar endpoints de consultas clínicas ou dados pessoais.

Essa separação aplica o princípio do menor privilégio.

---

## 9. Exercício 8 — Identificação de vulnerabilidades OWASP

Foram identificadas vulnerabilidades de categorias distintas.

### BOLA

Um usuário autenticado poderia tentar trocar o identificador de uma consulta na URL e acessar outro objeto.

Categoria:

- OWASP API1:2023 — Broken Object Level Authorization;
- OWASP A01:2021 — Broken Access Control.

Impacto:

- exposição de dados de saúde;
- alteração indevida de consultas;
- violação da confidencialidade dos pacientes.

### SQL Injection

Consultas construídas com concatenação de strings poderiam permitir alteração do comportamento do banco.

Categoria:

- OWASP A03:2021 — Injection.

Impacto:

- leitura;
- alteração;
- exclusão de dados;
- comprometimento do banco.

### XSS armazenado

O campo de observações poderia armazenar conteúdo JavaScript e executá-lo na página HTML da recepção.

Categoria:

- OWASP A03:2021 — Injection.

Impacto:

- execução de scripts no navegador;
- roubo de sessão;
- alteração da página;
- exposição de informações.

### Falhas de autenticação e configuração

Também foram identificados riscos de:

- autenticação insuficiente;
- CORS permissivo;
- falta de rate limiting;
- dependências vulneráveis;
- excesso de privilégios na integração externa.

---

## 10. Exercício 9 — Correção de entrada e saída

As vulnerabilidades identificadas foram corrigidas de forma centralizada.

Foram implementadas:

- validação por whitelist;
- regex para usernames e nomes de clientes;
- validação de UUIDs;
- validação de datas com fuso horário;
- validação de enums;
- limite de tamanho dos campos;
- `extra="forbid"` nos modelos aplicáveis;
- queries SQLModel parametrizadas;
- escape automático do Jinja2;
- verificação de ownership;
- prevenção de conflito de horários.

Também foi corrigido o endpoint da agenda HTML, que compartilhava o mesmo risco de exposição e XSS.

Os testes comprovaram:

- rejeição de username inválido;
- rejeição de campos extras;
- rejeição de datas malformadas;
- bloqueio de conflito de horário;
- escape do payload XSS;
- bloqueio de acesso a consulta de outro profissional.

---

## 11. Exercício 10 — Hardening de rede e proteção contra abuso

Foi configurado CORS com allowlist explícita.

As origens não autorizadas são rejeitadas e não foi utilizado wildcard para rotas protegidas.

Também foram adicionados headers de segurança:

- `Strict-Transport-Security`;
- `X-Frame-Options: DENY`;
- `X-Content-Type-Options: nosniff`.

Foi implementado rate limiting específico para o login, configurado pelo `BaseSettings`.

A configuração padrão utiliza:

- máximo de 5 tentativas;
- janela de 60 segundos.

Após exceder o limite, o endpoint retorna HTTP 429.

Foram criados testes para:

- permitir origem autorizada;
- rejeitar origem não autorizada;
- confirmar a presença dos headers;
- bloquear excesso de tentativas de login.

---

## 12. Exercício 11 — Persistência segura

A persistência foi migrada para SQLModel.

As sessões são fornecidas às rotas por injeção de dependência através da função `get_session`.

As consultas são construídas com `select()` e expressões parametrizadas, sem concatenação manual de SQL.

As credenciais e configurações do banco são carregadas pelo `BaseSettings`.

Foi utilizado o arquivo `.env` local para configurações de execução e criado o arquivo `.env.example` sem segredos reais.

O arquivo `.env` não deve ser versionado.

O ambiente local utiliza SQLite, enquanto a URL do banco pode ser configurada por variável de ambiente para o ambiente de produção.

Também foi configurado o `.gitignore` para impedir o versionamento de:

- `.env`;
- banco SQLite;
- ambiente virtual;
- cache;
- artefatos temporários.

---

## 13. Exercício 12 — Pipeline DevSecOps

Foi criado o workflow `.github/workflows/security.yml`.

O pipeline executa:

1. checkout do código;
2. instalação das dependências;
3. testes funcionais;
4. testes interativos de segurança;
5. análise SAST com Bandit;
6. análise SCA com pip-audit;
7. inicialização temporária da API;
8. scan passivo com OWASP ZAP;
9. avaliação dos relatórios;
10. Security Gate final.

A política definida bloqueia o pipeline quando:

- um teste falha;
- o Bandit encontra risco High;
- o pip-audit encontra dependência vulnerável;
- uma vulnerabilidade não possui score verificável;
- o ZAP encontra alerta High ou Critical;
- uma etapa obrigatória termina com erro.

O limite principal adotado foi CVSS 7.0.

Durante a execução inicial, o SCA bloqueou o pipeline por dependências vulneráveis. As dependências foram atualizadas e o pipeline passou posteriormente.

O resultado final comprovou aprovação de:

- testes funcionais;
- testes interativos;
- SAST;
- SCA;
- DAST;
- Security Gate Final.

---

## 14. Exercício 13 — Auditoria final e rastreabilidade

Foram adicionados testes unitários com mocking em `tests/test_exercicio13.py`.

Os testes cobrem:

- rejeição de campos extras;
- rejeição de username fora da regex;
- tratamento de erro na decodificação JWT;
- rejeição de algoritmo JWT não autorizado;
- bloqueio de acesso a consulta de outro profissional;
- consulta de usuário utilizando sessão mockada;
- auditoria da especificação OpenAPI;
- ausência de campos sensíveis na documentação.

Os testes específicos do Exercício 13 apresentaram:

`8 passed`

A suíte completa apresentou:

`28 passed`

A especificação OpenAPI foi auditada para confirmar:

- esquema OAuth2;
- token URL `/auth/token`;
- escopo `agenda:horarios`;
- proteção das rotas sensíveis;
- ausência de `senha_hash`;
- ausência de `client_secret_hash`.

### OWASP ZAP

Foi executado um scan passivo com OWASP ZAP 2.17.0.

O relatório final apresentou:

- High: 0;
- Medium: 0;
- Low: 0;
- Informational: 1;
- False Positives: 0.

O alerta informativo final foi:

- `Non-Storable Content`;
- plugin 10049;
- CWE-524;
- WASC-13;
- duas instâncias, nas rotas `/` e `/robots.txt`.

Esse resultado indica que as respostas não são armazenáveis por caches compartilhados. Isso é desejável para uma API que trabalha com informações pessoais e de saúde.

Para obter esse comportamento, foram adicionados:

- `Cache-Control: no-store, no-cache, must-revalidate, private`;
- `Pragma: no-cache`;
- `Expires: 0`.

O alerta inicial era `Storable and Cacheable Content`. Após a correção, o alerta foi substituído por `Non-Storable Content`, confirmando que a aplicação passou a impedir o armazenamento das respostas.

---

## 15. Rastreabilidade dos principais riscos

### BOLA

- CVSS estimado: 8.1;
- impacto: crítico;
- categoria: Broken Access Control;
- correção: ownership por usuário e profissional;
- evidência: testes de acesso negado.

### SQL Injection

- CVSS estimado: 9.8;
- impacto: crítico;
- categoria: Injection;
- correção: SQLModel e consultas parametrizadas;
- evidência: testes de entrada e revisão da camada de persistência.

### XSS armazenado

- CVSS estimado: 6.1;
- impacto: alto;
- categoria: Injection;
- correção: autoescape do Jinja2;
- evidência: teste com payload JavaScript.

### Comprometimento de autenticação

- CVSS estimado: 9.8;
- impacto: crítico;
- categoria: Identification and Authentication Failures;
- correção: JWT, bcrypt, expiração, MFA e validação de claims;
- evidência: testes de autenticação.

### Força bruta

- CVSS estimado: 7.5;
- impacto: alto;
- categoria: Identification and Authentication Failures;
- correção: rate limiting no login;
- evidência: teste de excesso de tentativas.

### CORS e configuração HTTP

- CVSS estimado: 6.5;
- impacto: médio/alto;
- categoria: Security Misconfiguration;
- correção: allowlist e headers de segurança;
- evidência: testes de CORS e pipeline.

### Dependências vulneráveis

- impacto: alto;
- categoria: Vulnerable and Outdated Components;
- correção: atualização das versões e uso do pip-audit;
- evidência: SCA aprovado no GitHub Actions.

### Cache de respostas sensíveis

- severidade ZAP: Informational;
- CWE: 524;
- correção: headers `Cache-Control`, `Pragma` e `Expires`;
- evidência: relatório final do ZAP.

---

## 16. Riscos residuais

O OWASP ZAP e os testes automatizados não validam completamente:

- configuração de TLS no ambiente de produção;
- proteção do servidor reverso;
- criptografia e restauração dos backups;
- rotação operacional das chaves;
- retenção e acesso aos logs;
- monitoramento contínuo;
- resposta a incidentes;
- segurança física e operacional do banco.

A decisão é autorizar a liberação de forma condicional.

A aplicação está aprovada tecnicamente pelo pipeline, mas o deploy só deve ocorrer se:

- HTTPS estiver obrigatório;
- o segredo JWT estiver em um mecanismo seguro;
- os backups estiverem protegidos;
- as permissões do banco estiverem restritas;
- houver monitoramento e controle de logs.

Caso essas condições não sejam atendidas, a liberação para produção deve ser bloqueada.

---


## 18. Conclusão

Ao longo dos 13 exercícios, a aplicação evoluiu de um esqueleto FastAPI para uma API modular com autenticação, autorização, ownership, integração M2M, validação rigorosa, persistência segura, proteção contra XSS, CORS controlado, headers de segurança, rate limiting, pipeline DevSecOps, testes automatizados e auditoria final.

Os principais riscos identificados no threat model foram tratados por controles implementados no código e validados por testes automatizados, ferramentas SAST, SCA e DAST.

O resultado final foi aprovado pelo Security Gate, sem alertas High, Medium ou Low no relatório final do OWASP ZAP.