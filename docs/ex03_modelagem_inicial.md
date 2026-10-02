1. Contexto e objetivo

A aplicação de agendamento de consultas trata informações relacionadas a pacientes, profissionais de saúde e consultas. Esses dados podem revelar informações pessoais e, dependendo do conteúdo, informações relacionadas à saúde.

Por esse motivo, a segurança deve ser considerada desde a modelagem inicial da aplicação. Este documento analisa a API sob a perspectiva da tríade CIA — confidencialidade, integridade e disponibilidade —, relaciona os principais riscos a frameworks de segurança reconhecidos e apresenta um DFD básico com os fluxos de dados e as fronteiras de confiança do sistema.

2. Escopo da análise

A análise considera os seguintes componentes:

API REST desenvolvida com FastAPI;

rotas organizadas com APIRouter;

modelos Pydantic para validação e controle das respostas;

persistência utilizando SQLModel;

banco de dados relacional;

página HTML interna para consulta da agenda;

frontend que consome a API em JSON;

integração externa com laboratório parceiro;

dados de pacientes, profissionais e consultas.

A versão analisada já possui alguns controles básicos:

separação entre rotas, modelos e banco de dados;

validação dos campos recebidos pela API;

consultas ao banco utilizando SQLModel;

uso de modelos de resposta para limitar os campos retornados;

uso de templates Jinja2 com escape automático;

testes automatizados para os principais caminhos disponíveis.

Também foram identificadas lacunas importantes:

ausência de autenticação obrigatória em todas as rotas;

ausência de verificação de ownership dos objetos;

ausência de diferenciação efetiva entre os papéis de usuário;

ausência de autenticação específica para a integração M2M;

ausência de rate limiting;

ausência de uma rotina completa de auditoria e monitoramento.

Essas lacunas são registradas como riscos da versão atual e devem ser consideradas antes de uma exposição em produção.

3. Inventário de ativos

Código

Ativo

Descrição

Impacto

A-01

Dados do paciente

Identificador e informações associadas ao paciente

Alto

A-02

Dados do profissional

Identificador do profissional responsável pela consulta

Alto

A-03

Registro da consulta

Data, hora, status, observações e relacionamentos

Alto

A-04

Agenda da clínica

Conjunto de horários e consultas disponíveis

Alto

A-05

Configurações da aplicação

Banco de dados, chaves, tokens e parâmetros operacionais

Alto

A-06

Disponibilidade do serviço

Capacidade da API de responder às requisições

Médio/alto

Os ativos A-01, A-02 e A-03 merecem proteção especial porque podem ser relacionados a pessoas identificáveis e a atendimentos médicos.

4. Análise pela tríade CIA

4.1 Confidencialidade

A confidencialidade garante que os dados sejam acessados somente por pessoas, sistemas e perfis autorizados.

Na aplicação, os principais riscos de confidencialidade são:

consulta de dados por usuários não autenticados;

acesso de um usuário ao registro de outra pessoa;

exposição de campos internos ou administrativos;

retorno de dados além do necessário;

vazamento de informações na página HTML;

exposição de credenciais em arquivos de configuração;

acesso excessivo pela integração externa.

Controles já presentes:

uso de modelos de resposta para controlar os campos públicos;

exclusão de campos internos, como informações de criação do registro;

escape automático dos valores exibidos nos templates;

separação entre a camada de persistência e a camada de apresentação.

Lacunas identificadas:

não há autenticação centralizada;

não há verificação de autorização por recurso;

não há escopos específicos para o laboratório;

não há política completa de minimização de dados em todas as respostas.

A confidencialidade é o requisito prioritário, pois a exposição de informações de saúde pode causar danos ao paciente e à clínica.

4.2 Integridade

A integridade garante que os dados sejam criados, alterados e excluídos somente por operações autorizadas e válidas.

Os principais riscos são:

alteração indevida de uma consulta;

criação de consultas com identificadores inválidos;

alteração do status por usuário sem permissão;

manipulação de data e hora;

inclusão de campos que não fazem parte do contrato da API;

alteração direta do banco por meio de entradas maliciosas;

execução de comandos ou consultas construídas de forma insegura.

Controles já presentes:

validação explícita dos dados recebidos;

uso de tipos definidos nos modelos Pydantic;

rejeição de campos desconhecidos onde extra="forbid" está configurado;

uso de SQLModel para acesso estruturado ao banco;

ausência de concatenação manual de strings para formar consultas SQL;

testes automatizados dos fluxos principais.

Lacunas identificadas:

ausência de controle de ownership;

ausência de RBAC ou ABAC aplicado às rotas;

ausência de trilha de auditoria para alterações;

ausência de regras completas para impedir conflitos de agenda.

4.3 Disponibilidade

A disponibilidade garante que a API e a agenda estejam acessíveis quando forem necessárias.

Os principais riscos são:

excesso de requisições;

consultas muito pesadas;

indisponibilidade do banco;

falhas não tratadas;

ausência de monitoramento;

falta de backup e procedimento de recuperação;

consumo abusivo por integrações externas.

Controles já presentes:

organização modular, facilitando manutenção;

uso de testes automatizados;

persistência estruturada em banco de dados;

separação das responsabilidades entre os módulos;

tratamento padrão de validação da FastAPI.

Lacunas identificadas:

ausência de rate limiting;

ausência de métricas e alertas;

ausência de estratégia documentada de backup;

ausência de limites específicos para consultas;

ausência de mecanismo de circuit breaker para dependências externas.

5. Mapeamento com frameworks de segurança

5.1 OWASP

Referência

Risco relacionado

Controle observado

Situação

OWASP API3 — Broken Object Level Authorization

Usuário acessa uma consulta informando outro identificador

Ainda não existe verificação de ownership

Lacuna

OWASP A01 — Broken Access Control

Acesso às rotas sem autorização por papel

As rotas ainda não aplicam autorização por perfil

Lacuna

OWASP A03 — Injection

Entrada maliciosa alterando consultas ou comandos

Uso de SQLModel e ausência de concatenação manual de SQL

Parcialmente controlado

OWASP A03 — XSS

Observação maliciosa executada na página HTML

Jinja2 utiliza escape automático por padrão

Controlado no template

OWASP A05 — Security Misconfiguration

Configurações inseguras de CORS, headers ou ambiente

Algumas configurações ainda não foram endurecidas

Lacuna

OWASP A07 — Identification and Authentication Failures

Acesso sem autenticação forte

Não há autenticação obrigatória na versão analisada

Lacuna

OWASP A09 — Logging and Monitoring Failures

Alterações e acessos sem rastreabilidade

Não há auditoria completa das operações

Lacuna

A análise demonstra que validação, parametrização e escape de saída reduzem alguns riscos, mas não substituem autenticação e autorização.

5.2 NIST SSDF

Prática do NIST SSDF

Aplicação na API

Situação

PW.1 — Projetar o software considerando requisitos de segurança

A tríade CIA e o DFD definem os objetivos de proteção

Aplicado

PW.2 — Revisar o projeto do software

As fronteiras de confiança e os fluxos sensíveis foram identificados

Aplicado

PW.5 — Utilizar práticas de codificação segura

Foram usados modelos tipados, validação e templates com escape

Parcialmente aplicado

PW.6 — Configurar o software com definições seguras

O modelo de resposta restringe a exposição de campos

Parcialmente aplicado

PW.7 — Revisar o código legível

A separação em módulos facilita a revisão por responsabilidade

Aplicado

PW.8 — Testar o código executável

Existem testes automatizados para os fluxos principais

Parcialmente aplicado

RV.1 — Identificar vulnerabilidades

Os riscos de BOLA, XSS, injeção e acesso indevido foram registrados

Aplicado

RV.2 — Avaliar e priorizar vulnerabilidades

A confidencialidade dos dados de saúde foi classificada como prioridade alta

Aplicado

O mapeamento mostra que a segurança foi considerada no desenho e na implementação inicial, mas ainda existem controles necessários para uma operação completa.

5.3 MITRE ATT&CK

Técnica MITRE

Possível aplicação no sistema

Controle ou necessidade

T1190 — Exploit Public-Facing Application

Exploração de uma rota pública ou exposta

Validação, autenticação, autorização e monitoramento

T1078 — Valid Accounts

Uso indevido de contas legítimas

MFA, expiração de sessão e menor privilégio

T1110 — Brute Force

Tentativas repetidas de autenticação

Rate limiting e bloqueio progressivo

T1552.001 — Credentials In Files

Exposição de chaves ou senhas em arquivos

Uso de variáveis de ambiente e ausência de segredos no repositório

T1565.001 — Stored Data Manipulation

Alteração indevida de registros persistidos

Controle de autorização, validação e auditoria

A utilização do MITRE ajuda a relacionar os riscos técnicos às formas pelas quais um atacante poderia explorar a aplicação.

6. Diagrama de fluxo de dados

flowchart TD
    FE["Frontend JSON"]
    REC["Recepção / Navegador"]
    LAB["Laboratório parceiro"]
    API["API FastAPI"]
    DB[("Banco SQLModel")]

    FE -->|"Requisições JSON"| API
    REC -->|"Consulta da agenda"| API
    LAB -->|"Consulta de disponibilidade"| API
    API -->|"SELECT e INSERT parametrizados"| DB
    DB -->|"Registros de consultas"| API
    API -->|"Resposta JSON"| FE
    API -->|"HTML escapado"| REC
    API -->|"Horários mínimos necessários"| LAB

O laboratório aparece no DFD como consumidor externo. A integração deve receber somente os dados necessários para consultar disponibilidade, evitando o envio de informações pessoais ou observações clínicas.

7. Fluxos de dados sensíveis

Fluxo

Origem

Destino

Dados envolvidos

Riscos principais

F-01

Frontend

API

Identificadores, data, hora, status e observações

Interceptação, entrada inválida e acesso indevido

F-02

Recepção

API

Data da agenda e registros de consulta

Exposição de dados na resposta HTML

F-03

API

Banco de dados

Registros completos das consultas

Injeção, acesso excessivo e alteração indevida

F-04

Banco de dados

API

Consultas filtradas

Retorno de dados além do necessário

F-05

Laboratório

API

Consulta de horários disponíveis

Token comprometido e excesso de privilégio

Os campos de observação devem ser tratados como dados potencialmente sensíveis. Eles não devem ser exibidos sem escape nem enviados a consumidores que não precisam desse conteúdo.

8. Fronteiras de confiança

TB-01 — Clientes externos e API

Inclui o frontend, a página utilizada pela recepção e o laboratório parceiro.

Riscos:

requisições falsificadas;

alteração de parâmetros;

tentativa de enumeração de identificadores;

envio de payloads maliciosos;

abuso de requisições.

Controles necessários:

autenticação;

autorização por papel e por recurso;

validação de entrada;

comunicação protegida;

limitação de requisições;

mensagens de erro sem informações internas.

TB-02 — API e banco de dados

É a fronteira entre o processo da aplicação e a persistência.

Riscos:

acesso excessivo ao banco;

credenciais expostas;

consultas inseguras;

alteração não rastreada;

vazamento de dados em mensagens de erro.

Controles necessários:

credenciais fora do código;

permissões mínimas;

consultas parametrizadas;

sessões controladas;

logs de operações relevantes;

backup protegido.

TB-03 — API e navegador da recepção

É a fronteira responsável pela renderização da agenda em HTML.

Riscos:

XSS armazenado;

exposição de campos internos;

conteúdo HTML não confiável;

inclusão de informações além do necessário.

Controles já observados:

uso de Jinja2;

escape automático das variáveis;

modelo específico para apresentação dos dados.

TB-04 — Laboratório e API

É a fronteira da comunicação máquina-a-máquina.

Riscos:

token comprometido;

reutilização de credenciais;

acesso a endpoints fora do contrato;

consulta de informações de pacientes;

ausência de rastreabilidade.

Controles necessários:

credencial própria para a integração;

escopos limitados;

expiração e rotação de tokens;

respostas minimizadas;

registro das requisições.

9. Requisitos de segurança derivados da análise

A partir dos ativos, fluxos e fronteiras identificados, a aplicação deve observar os seguintes requisitos:

Cada rota deve exigir somente as permissões necessárias para sua operação.

O acesso a uma consulta deve considerar o usuário autenticado e o recurso solicitado.

Os modelos de entrada devem aceitar somente os campos previstos no contrato.

Os modelos de saída devem retornar somente os campos necessários ao consumidor.

Os dados exibidos em HTML devem utilizar escape de saída.

As consultas ao banco devem permanecer parametrizadas.

Segredos, senhas e tokens não devem ser gravados no código-fonte.

A integração externa deve receber o menor conjunto de dados possível.

Operações relevantes devem ser registradas para permitir auditoria.

A aplicação deve possuir controles contra abuso e indisponibilidade.

Mensagens de erro não devem revelar stack traces, credenciais ou detalhes internos.

O banco deve ser protegido por permissões mínimas e backups controlados.

10. Validação crítica

A análise também possui algumas limitações importantes:

Um UUID dificulta a adivinhação do identificador, mas não substitui autorização.

A validação Pydantic garante formato e tipos, mas não garante que o usuário tenha permissão para acessar o objeto.

O escape automático do Jinja2 reduz XSS, mas não protege código que utilize conteúdo não confiável com |safe.

A parametrização das consultas reduz SQL Injection, mas não impede falhas de regra de negócio.

O modelo de resposta reduz exposição acidental, mas não impede acesso indevido antes da serialização.

Um DFD documenta os fluxos e limites, mas não comprova que todos os controles estejam ativos.

Testes funcionais positivos não são suficientes para comprovar autorização, resistência a abuso ou proteção contra todos os ataques.

Portanto, os controles implementados devem ser avaliados junto com os controles ausentes. A aplicação possui uma base inicial segura, mas ainda exige autenticação, autorização, auditoria, proteção de infraestrutura e monitoramento para operar com dados reais.

11. Conclusão

A análise identificou que a API já possui controles importantes de estrutura, validação, persistência parametrizada, limitação de campos de resposta e escape de conteúdo HTML.

Os riscos mais relevantes estão relacionados à confidencialidade e à integridade dos dados de saúde. Os principais pontos de atenção são a ausência de autenticação obrigatória, autorização por recurso, diferenciação de papéis, proteção específica para a integração externa, auditoria e controles contra abuso.

O DFD e o mapeamento dos frameworks tornam visíveis os ativos protegidos, os pontos de entrada, as fronteiras de confiança e os controles necessários para reduzir os riscos da aplicação.