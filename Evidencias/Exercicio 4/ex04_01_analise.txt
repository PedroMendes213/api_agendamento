## 1. Objetivo

Este documento apresenta a modelagem de ameaças da API de agendamento de consultas utilizando:

- misuse cases;
- framework STRIDE;
- identificação de ativos;
- superfícies de ataque;
- fronteiras de confiança;
- ameaças;
- mitigações;
- riscos residuais.

A aplicação processa dados relacionados a consultas médicas. Por isso, uma falha de confidencialidade, integridade ou disponibilidade pode gerar impactos relevantes para pacientes, profissionais e clínicas.

---

## 2. Escopo analisado

Foram considerados os seguintes componentes:

- frontend que consome a API em JSON;
- navegador utilizado pela recepção;
- API FastAPI;
- rotas de consultas;
- modelos Pydantic e SQLModel;
- templates Jinja2;
- banco SQLite;
- documentação OpenAPI/Swagger;
- integração máquina-a-máquina com laboratório parceiro.

As principais rotas disponíveis são:

- `GET /consultas`;
- `POST /consultas`;
- `GET /consultas/{consulta_id}`;
- `PUT /consultas/{consulta_id}`;
- `DELETE /consultas/{consulta_id}`;
- `GET /agenda`;
- `GET /health`.

A análise considera o estado atual da aplicação e registra controles já implementados, controles parciais e riscos ainda abertos.

---

## 3. Metodologia utilizada

A análise foi realizada nas seguintes etapas:

1. identificação dos ativos que precisam de proteção;
2. identificação das fronteiras de confiança;
3. identificação das superfícies de ataque;
4. elaboração de misuse cases;
5. aplicação do STRIDE aos componentes principais;
6. classificação dos riscos e definição de mitigações.

O STRIDE foi aplicado aos seguintes componentes:

- rotas e camada HTTP da API;
- modelos de entrada e saída;
- templates Jinja2 e navegador;
- persistência e integração externa.

---

## 4. Ativos da aplicação

### A-01 — Dados das consultas

Incluem:

- identificador do paciente;
- identificador do profissional;
- data e horário da consulta;
- status;
- observações.

Impactos possíveis em caso de exposição ou alteração:

- violação de confidencialidade;
- exposição de informações relacionadas à saúde;
- alteração indevida de atendimentos;
- prejuízo aos pacientes e à clínica;
- descumprimento de princípios da LGPD.

Classificação:

- confidencialidade: alta;
- integridade: alta;
- disponibilidade: média.

### A-02 — Dados internos de auditoria

O campo `criado_em` é armazenado no banco para controle interno.

Esse campo não deve ser exposto nas respostas públicas da API.

Impactos possíveis em caso de exposição:

- revelação de detalhes internos;
- aumento da capacidade de reconhecimento da aplicação;
- apoio a ataques futuros.

### A-03 — Banco de dados

O banco armazena os registros das consultas e seus respectivos campos.

Impactos possíveis em caso de comprometimento:

- leitura indevida;
- alteração de consultas;
- exclusão de registros;
- indisponibilidade;
- cópia não autorizada do arquivo local.

### A-04 — Identidade e credenciais

A aplicação precisará proteger:

- contas de usuários;
- senhas;
- tokens;
- segredo utilizado para assinatura de tokens;
- credenciais de integração externa.

Impactos possíveis em caso de comprometimento:

- falsificação de identidade;
- acesso indevido;
- alteração de consultas;
- acesso a funções administrativas;
- abuso da integração com o laboratório.

### A-05 — Disponibilidade da API

A API precisa atender:

- frontend;
- recepção;
- profissionais de saúde;
- laboratório parceiro.

Impactos possíveis em caso de indisponibilidade:

- impossibilidade de consultar a agenda;
- atrasos no atendimento;
- interrupção das integrações;
- prejuízo operacional.

---

## 5. Fronteiras de confiança

### TB-01 — Clientes e API

Essa fronteira separa os clientes externos da aplicação FastAPI.

Clientes envolvidos:

- frontend;
- navegador da recepção;
- laboratório parceiro.

Os dados atravessam essa fronteira por requisições HTTP e podem conter informações sensíveis.

Ameaças principais:

- falsificação de identidade;
- manipulação de requisições;
- envio de payloads maliciosos;
- interceptação de dados;
- abuso dos endpoints.

### TB-02 — Aplicação e banco de dados

Essa fronteira separa o processo FastAPI do banco SQLite.

Ameaças principais:

- consultas inseguras;
- acesso direto ao arquivo;
- alteração dos dados;
- cópia não autorizada;
- indisponibilidade causada por bloqueios ou corrupção.

### TB-03 — Aplicação e navegador da recepção

Essa fronteira separa a aplicação responsável por gerar o HTML do navegador que renderiza a agenda.

Ameaças principais:

- XSS armazenado;
- exposição de informações para usuários indevidos;
- manipulação da página;
- captura de sessão em um cenário autenticado.

### TB-04 — Laboratório parceiro e API

Essa fronteira representa a integração máquina-a-máquina.

Ameaças principais:

- token comprometido;
- excesso de privilégios;
- reutilização de credenciais;
- acesso a operações fora do contrato;
- ausência de validação de escopo.

---

## 6. Superfícies de ataque

### S-01 — Corpo JSON das requisições

Os endpoints de criação e atualização recebem dados enviados pelo cliente.

Possíveis ataques:

- inclusão de campos não declarados;
- valores inválidos;
- payloads muito grandes;
- conteúdo HTML ou JavaScript;
- tentativa de alterar campos internos.

Controles atuais:

- modelos Pydantic;
- `extra="forbid"`;
- validação de UUID;
- validação por Enum;
- limite de tamanho de `observacoes`;
- validação de fuso horário.

### S-02 — Identificador da consulta na URL

As rotas utilizam:

```text
/consultas/{consulta_id}

Possíveis ataques:
- troca do UUID por outro identificador;
- acesso à consulta de outro paciente;
- alteração de registro de terceiros;
- exclusão indevida.
Controle necessário:
- autenticação;
- autorização por recurso;
- verificação de ownership;
- validação do relacionamento entre usuário e consulta.
S-03 — Página HTML da agenda
A rota /agenda apresenta no navegador dados persistidos das consultas.
Possíveis ataques:
- inserção de HTML malicioso;
- XSS armazenado;
- roubo de sessão em um cenário autenticado;
- alteração visual da página.
Controles atuais:
- Jinja2;
- autoescape habilitado;
- ausência do filtro safe;
- teste automatizado contra XSS.
S-04 — Documentação OpenAPI
A documentação Swagger é disponibilizada pela rota:
/docs

Possíveis riscos:
- exposição dos endpoints;
- descoberta de parâmetros;
- reconhecimento da estrutura da aplicação;
- facilitação de ataques automatizados.
A documentação é útil durante o desenvolvimento, mas deve ser protegida ou restringida em um ambiente de produção.
S-05 — Banco SQLite
O arquivo local contém os registros persistidos das consultas.
Possíveis ataques:
- cópia direta do arquivo;
- leitura dos registros fora da aplicação;
- alteração ou exclusão dos dados;
- corrupção do banco;
- exploração de permissões inadequadas no sistema operacional.
7. Misuse cases
MC-01 — Acesso à consulta de outro paciente
Ator:
- usuário malicioso ou usuário autenticado sem autorização adequada.
Ativo afetado:
- dados da consulta.
Pré-condição:
- o atacante possui ou descobre um identificador de consulta.
Fluxo do abuso:
1. o atacante acessa uma consulta autorizada;
2. altera o valor de consulta_id na URL;
3. envia uma nova requisição;
4. a aplicação retorna outra consulta sem validar ownership.
Impacto:
- exposição de dados de saúde;
- violação de confidencialidade;
- alteração ou exclusão de registros de terceiros.
Categorias relacionadas:
- Broken Object Level Authorization;
- Broken Access Control;
- STRIDE: Spoofing, Tampering e Information Disclosure.
Mitigações:
- autenticação;
- autorização por papel;
- verificação de ownership;
- autorização por recurso;
- testes automatizados com troca de identificadores;
- logs das operações sensíveis.
Situação atual:
- risco aberto, pois a API ainda não possui autenticação e ownership.
MC-02 — Inserção de script nas observações
Ator:
- usuário malicioso.
Ativo afetado:
- navegador da recepção;
- conteúdo da agenda.
Pré-condição:
- o atacante consegue criar ou alterar uma consulta.
Fluxo do abuso:
1. o atacante envia o valor:
<script>alert('xss')</script>

2. a aplicação persiste a observação;
3. a recepção acessa a agenda;
4. o navegador renderiza o conteúdo.
Impacto:
- execução de JavaScript;
- manipulação da página;
- roubo de dados;
- captura de sessão em um cenário autenticado.
Categorias relacionadas:
- XSS armazenado;
- Injection;
- STRIDE: Tampering e Information Disclosure.
Mitigações:
- autoescape do Jinja2;
- não utilização do filtro safe;
- validação de saída;
- teste automatizado contra conteúdo HTML.
Situação atual:
- mitigado na página HTML;
- o teste automatizado comprova que o script é exibido como texto.
MC-03 — Tentativa de enviar campo interno
Ator:
- cliente malicioso.
Ativo afetado:
- integridade dos dados;
- informações internas de auditoria.
Pré-condição:
- o atacante conhece ou adivinha o nome de um campo interno.
Fluxo do abuso:
1. o atacante envia o campo criado_em;
2. tenta alterar a data original de criação;
3. tenta realizar mass assignment;
4. espera que o campo seja persistido ou devolvido na resposta.
Impacto:
- adulteração da trilha de auditoria;
- perda de confiabilidade dos registros;
- exposição de informações internas.
Mitigações:
- modelos separados para entrada e saída;
- extra="forbid";
- ausência do campo interno no modelo de criação;
- ausência de criado_em no response model.
Situação atual:
- mitigado pelos modelos de validação e resposta.
MC-04 — Enumeração de consultas sem autenticação
Ator:
- usuário não autenticado.
Ativo afetado:
- dados das consultas.
Pré-condição:
- endpoint acessível sem autenticação.
Fluxo do abuso:
1. o atacante acessa GET /consultas;
2. utiliza os parâmetros de paginação;
3. coleta identificadores, horários e observações;
4. automatiza as requisições.
Impacto:
- vazamento em massa;
- exposição de dados sensíveis;
- reconhecimento da base de dados.
Mitigações:
- autenticação obrigatória;
- autorização por papel;
- autorização por objeto;
- limitação de paginação;
- rate limiting;
- registros de auditoria;
- monitoramento.
Situação atual:
- o limite de paginação reduz o volume por requisição;
- a autenticação ainda não está presente.
MC-05 — Força bruta contra o login
Ator:
- atacante externo.
Ativo afetado:
- contas de profissionais e administradores.
Pré-condição:
- existência de um endpoint de login.
Fluxo do abuso:
1. o atacante envia várias combinações de usuário e senha;
2. observa as respostas;
3. tenta descobrir credenciais válidas;
4. utiliza a conta comprometida para acessar consultas.
Impacto:
- acesso indevido;
- exposição de dados;
- alteração de consultas;
- abuso de privilégios.
Mitigações:
- armazenamento de senha com bcrypt;
- rate limiting;
- bloqueio progressivo;
- expiração de tokens;
- MFA;
- monitoramento de tentativas.
Situação atual:
- o endpoint de login ainda não está presente;
- o risco deve ser considerado no desenho da autenticação.
MC-06 — Token do laboratório com excesso de privilégios
Ator:
- atacante que obteve um token válido do laboratório.
Ativo afetado:
- dados das consultas;
- escopo da integração externa.
Pré-condição:
- token do laboratório comprometido.
Fluxo do abuso:
1. o atacante utiliza o token legítimo;
2. tenta criar, alterar ou excluir consultas;
3. acessa dados fora do objetivo da integração;
4. explora permissões excessivas.
Impacto:
- violação de confidencialidade;
- alteração de dados;
- abuso da integração externa.
Mitigações:
- OAuth2 Client Credentials;
- escopos específicos;
- claims de identidade;
- princípio do menor privilégio;
- expiração de tokens;
- validação de emissor e audiência.
Situação atual:
- a integração externa ainda não está ativa;
- o controle deve ser definido antes da exposição do serviço ao laboratório.
8. Aplicação do STRIDE
8.1 Componente C-01 — Rotas FastAPI e API REST
Spoofing
Ameaça:
Um usuário pode se passar por outro usuário porque as rotas atuais não exigem autenticação.
Mitigações:
- OAuth2PasswordBearer;
- JWT;
- validação da assinatura;
- expiração de tokens;
- MFA para contas administrativas.
Situação:
- ameaça aberta.
Tampering
Ameaça:
Um usuário pode alterar ou excluir uma consulta que não deveria controlar.
Mitigações:
- ownership;
- autorização por recurso;
- RBAC;
- validação de papel;
- auditoria das operações.
Situação:
- ameaça aberta.
Repudiation
Ameaça:
Um usuário pode negar que criou, alterou ou excluiu uma consulta.
Mitigações:
- logs estruturados;
- identificação do usuário;
- timestamp;
- registro da operação;
- identificador de correlação.
Situação:
- o campo criado_em existe, mas a auditoria completa ainda não está implementada.
Information Disclosure
Ameaça:
A API pode retornar consultas ou campos internos para um cliente sem autorização.
Mitigações:
- response models;
- autenticação;
- ownership;
- RBAC;
- minimização de dados.
Situação:
- o response model já restringe os campos;
- a autorização ainda é necessária.
Denial of Service
Ameaça:
Um cliente pode realizar muitas requisições ou solicitar volume excessivo de dados.
Mitigações:
- paginação;
- limite máximo de 100 registros;
- rate limiting;
- timeouts;
- monitoramento.
Situação:
- paginação implementada;
- rate limiting ainda ausente.
Elevation of Privilege
Ameaça:
Um usuário comum pode tentar executar operações administrativas.
Mitigações:
- RBAC;
- escopos;
- claims;
- MFA;
- verificação centralizada de permissões.
Situação:
- ameaça aberta.
8.2 Componente C-02 — Modelos de entrada e saída
Spoofing
Ameaça:
O cliente pode enviar um identificador de paciente ou profissional que não representa sua identidade real.
Mitigações:
- autenticação;
- associação entre usuário autenticado e profissional;
- verificação de ownership.
Situação:
- a aplicação valida o formato do UUID, mas ainda não valida a identidade associada.
Tampering
Ameaça:
O cliente pode tentar alterar campos internos ou adicionar propriedades não previstas.
Mitigações:
- extra="forbid";
- modelos separados para criação, leitura e atualização;
- campos internos definidos somente no modelo persistido.
Situação:
- mitigado.
Repudiation
Ameaça:
Não é possível relacionar completamente uma alteração a um usuário específico.
Mitigações:
- auditoria de usuário;
- logs;
- timestamp;
- registro das alterações.
Situação:
- parcialmente tratado pelo campo interno de criação;
- auditoria completa ainda ausente.
Information Disclosure
Ameaça:
Campos internos podem ser incluídos nas respostas.
Mitigações:
- ConsultaRead;
- from_attributes=True;
- lista explícita de campos públicos.
Situação:
- mitigado.
Denial of Service
Ameaça:
O cliente pode enviar observações excessivamente grandes ou payloads inválidos em grande quantidade.
Mitigações:
- max_length=1000;
- limite de paginação;
- limite de tamanho do corpo da requisição;
- rate limiting.
Situação:
- parcialmente mitigado.
Elevation of Privilege
Ameaça:
O cliente pode tentar enviar campos que representem permissões ou papéis.
Mitigações:
- modelos de entrada sem campos de autorização;
- extra="forbid";
- autorização centralizada.
Situação:
- a validação de campos está implementada;
- a autorização ainda é necessária.
8.3 Componente C-03 — Templates Jinja2 e navegador
Spoofing
Ameaça:
Uma página falsa pode tentar se passar pela agenda oficial.
Mitigações:
- HTTPS;
- autenticação;
- controle de origem;
- proteção de sessão;
- cookies seguros.
Situação:
- controles de produção ainda não estão configurados.
Tampering
Ameaça:
Conteúdo malicioso pode ser inserido nas observações das consultas.
Mitigações:
- autoescape;
- ausência do filtro safe;
- validação de saída;
- testes de XSS.
Situação:
- mitigado.
Repudiation
Ameaça:
Não há registro suficiente de quem inseriu um conteúdo malicioso.
Mitigações:
- identificação do usuário;
- logs;
- timestamp;
- trilha de auditoria.
Situação:
- ainda incompleto.
Information Disclosure
Ameaça:
A página pode exibir dados para uma pessoa sem autorização.
Mitigações:
- autenticação;
- autorização da rota;
- minimização dos dados exibidos;
- proteção de sessão.
Situação:
- a saída é controlada;
- o acesso à página ainda precisa ser protegido.
Denial of Service
Ameaça:
A página pode ser solicitada repetidamente ou processar dados excessivos.
Mitigações:
- paginação;
- limite de resultados;
- rate limiting;
- cache controlado.
Situação:
- parcialmente mitigado.
Elevation of Privilege
Ameaça:
Conteúdo HTML malicioso pode tentar capturar uma sessão administrativa.
Mitigações:
- autoescape;
- cookies seguros;
- Content Security Policy;
- MFA;
- separação de perfis.
Situação:
- autoescape implementado;
- os demais controles ainda são necessários.
8.4 Componente C-04 — Banco de dados e integração externa
Spoofing
Ameaça:
Um processo não autorizado pode tentar acessar diretamente o banco ou utilizar uma integração externa sem identidade validada.
Mitigações:
- permissões do sistema operacional;
- credenciais externas ao código;
- autenticação M2M;
- validação de emissor e audiência.
Situação:
- proteção operacional e integração M2M ainda não estão configuradas.
Tampering
Ameaça:
Um atacante pode tentar alterar os dados diretamente ou explorar consultas inseguras.
Mitigações:
- SQLModel;
- queries estruturadas;
- transações;
- controle de acesso ao arquivo;
- backup.
Situação:
- as queries atuais utilizam SQLModel;
- a proteção do arquivo e o backup ainda precisam ser definidos.
Repudiation
Ameaça:
Alterações diretas no banco podem não gerar registro de auditoria.
Mitigações:
- logs;
- auditoria;
- controle de acesso;
- trilha de alterações.
Situação:
- auditoria completa ainda não está disponível.
Information Disclosure
Ameaça:
O arquivo do banco pode ser copiado e lido diretamente.
Mitigações:
- permissões restritas;
- armazenamento protegido;
- criptografia;
- banco gerenciado;
- separação entre aplicação e persistência.
Situação:
- risco presente no ambiente local.
Denial of Service
Ameaça:
O banco pode ser bloqueado, corrompido ou sobrecarregado.
Mitigações:
- backup;
- transações;
- monitoramento;
- banco adequado para produção;
- recuperação testada.
Situação:
- parcialmente tratado.
Elevation of Privilege
Ameaça:
Um usuário do sistema operacional pode obter acesso direto ao arquivo do banco.
Mitigações:
- princípio do menor privilégio;
- separação de usuários;
- permissões de arquivos;
- banco gerenciado com controle de acesso.
Situação:
- risco presente no ambiente local.
9. Registro consolidado de ameaças
T-01 — BOLA em consultas
- categoria: Broken Object Level Authorization;
- STRIDE: Tampering e Information Disclosure;
- severidade: crítica;
- ativo afetado: dados das consultas;
- situação: ameaça aberta;
- mitigação: autenticação, ownership e autorização por recurso.
T-02 — Acesso sem autenticação
- categoria: Broken Authentication e Broken Access Control;
- STRIDE: Spoofing e Information Disclosure;
- severidade: alta;
- ativo afetado: consultas médicas;
- situação: ameaça aberta;
- mitigação: JWT, RBAC, expiração de token e MFA.
T-03 — XSS armazenado
- categoria: Injection;
- STRIDE: Tampering e Information Disclosure;
- severidade: alta;
- ativo afetado: navegador da recepção;
- situação: mitigado na página HTML;
- mitigação: autoescape Jinja2 e teste automatizado.
T-04 — Mass assignment
- categoria: Security Misconfiguration e Tampering;
- STRIDE: Tampering;
- severidade: alta;
- ativo afetado: campos internos de auditoria;
- situação: mitigado;
- mitigação: extra="forbid" e modelos separados.
T-05 — SQL Injection
- categoria: Injection;
- STRIDE: Tampering e Information Disclosure;
- severidade: crítica;
- ativo afetado: banco de dados;
- situação: controlado nas consultas atuais;
- mitigação: SQLModel e queries estruturadas;
- observação: os testes de entrada continuam necessários para validar o comportamento.
T-06 — Enumeração e excesso de requisições
- categoria: Unrestricted Resource Consumption;
- STRIDE: Denial of Service;
- severidade: média;
- ativo afetado: disponibilidade da API;
- situação: parcialmente mitigado;
- controle atual: paginação e limite de 100 registros;
- mitigação necessária: rate limiting e monitoramento.
T-07 — Força bruta no login
- categoria: Identification and Authentication Failures;
- STRIDE: Spoofing;
- severidade: alta;
- ativo afetado: contas de usuários;
- situação: risco previsto para o componente de autenticação;
- mitigação: bcrypt, rate limiting, expiração de tokens e MFA.
T-08 — Token M2M com excesso de privilégios
- categoria: Broken Function Level Authorization;
- STRIDE: Spoofing, Information Disclosure e Elevation of Privilege;
- severidade: alta;
- ativo afetado: integração com o laboratório;
- situação: integração ainda não ativa;
- mitigação: escopos, claims, client credentials e menor privilégio.
T-09 — Acesso direto ao banco local
- categoria: Security Misconfiguration;
- STRIDE: Information Disclosure e Tampering;
- severidade: alta;
- ativo afetado: arquivo agendamento.db;
- situação: risco presente no ambiente local;
- mitigação: permissões de arquivo, backup, criptografia e banco de produção.
10. Prioridade das mitigações
As mitigações devem ser priorizadas da seguinte forma:
1. autenticação dos usuários;
2. autorização por papel;
3. ownership das consultas;
4. proteção contra BOLA;
5. autenticação da integração externa;
6. escopos e claims;
7. rate limiting;
8. headers de segurança;
9. proteção da documentação em produção;
10. auditoria detalhada;
11. banco adequado para produção;
12. monitoramento e backup.
11. Riscos residuais
Mesmo com as correções atuais, permanecem os seguintes riscos:
- ausência de autenticação;
- ausência de autorização por recurso;
- possibilidade de acesso indevido a consultas;
- ausência de rate limiting;
- exposição potencial da documentação Swagger;
- acesso direto ao arquivo SQLite;
- ausência de auditoria completa;
- ausência de proteção operacional de produção.
Esses riscos não devem ser considerados aceitáveis para uma implantação em produção enquanto não houver controles de identidade, autorização, proteção de rede e segurança da persistência.
12. Conclusão
A modelagem STRIDE demonstrou que os principais riscos da API estão relacionados ao controle de acesso, à proteção dos dados de saúde e à segurança das integrações externas.
A aplicação já possui controles importantes:
- validação de entrada;
- rejeição de campos desconhecidos;
- response models;
- proteção contra XSS;
- paginação;
- queries estruturadas com SQLModel.
Por outro lado, ainda existem riscos relevantes relacionados à autenticação, autorização, ownership, rate limiting, auditoria e proteção do banco local.
O risco mais grave identificado é o BOLA, pois a simples alteração de um identificador pode permitir o acesso a dados pertencentes a outra pessoa caso não exista uma verificação de autorização por objeto.
A liberação para produção deve permanecer bloqueada até que os riscos críticos de autenticação e autorização sejam tratados e testados.