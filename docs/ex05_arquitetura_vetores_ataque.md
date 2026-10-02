Exercício 5 — Arquitetura de segurança e vetores de ataque

1. Objetivo

Este documento apresenta a arquitetura de segurança da API de agendamento de consultas, dividindo o sistema em partições, identificando as fronteiras de confiança e descrevendo os fluxos de dados entre seus componentes.

Também são analisados vetores de ataque relacionados aos três eixos de segurança de APIs:

design;

implementação;

infraestrutura.

A aplicação trabalha com dados de pacientes, profissionais de saúde e consultas. Portanto, os controles de segurança devem considerar principalmente a confidencialidade, a integridade e o acesso mínimo necessário aos dados.

2. Particionamento do sistema

P1 — Clientes externos

Esta partição contém os consumidores que acessam a API:

frontend que consome respostas JSON;

navegador utilizado pela recepção;

laboratório parceiro que realiza integração máquina-a-máquina.

Esses consumidores devem ser considerados não confiáveis. Mesmo que o frontend ou o navegador sejam controlados pela própria clínica, os dados enviados nas requisições podem ser alterados pelo usuário.

P2 — Camada HTTP e API

Esta partição contém:

aplicação FastAPI;

rotas organizadas com APIRouter;

endpoints JSON;

endpoint HTML da agenda;

documentação OpenAPI;

tratamento inicial das requisições e respostas.

Essa é a principal superfície de exposição da aplicação. Todos os dados recebidos dos clientes devem ser validados antes de alcançar as regras de negócio ou o banco.

P3 — Validação, regras e segurança

Esta partição concentra as responsabilidades internas da aplicação:

modelos Pydantic;

validação dos campos;

regras de negócio;

controle de acesso;

verificação de ownership;

definição dos dados que podem ser retornados;

tratamento de erros.

A autenticação e a autorização devem permanecer centralizadas nessa camada. As rotas não devem implementar verificações de segurança diferentes para o mesmo tipo de operação.

Na versão analisada, a validação dos dados e o controle das respostas já estão presentes, mas ainda existem pontos de atenção relacionados à autenticação, aos papéis dos usuários e ao acesso individual às consultas.

P4 — Persistência

Esta partição contém:

camada database.py;

sessões de banco;

SQLModel;

banco SQLite utilizado no ambiente local;

registros de pacientes, profissionais e consultas.

O banco deve receber somente dados validados e consultas parametrizadas. As credenciais e configurações do banco não devem ficar diretamente gravadas no código-fonte.

P5 — Operação e configuração

Esta partição representa o ambiente em que a aplicação é executada:

sistema operacional;

servidor Uvicorn;

configurações de ambiente;

rede;

logs;

backups;

monitoramento;

exposição das portas e da documentação.

Mesmo que o código esteja correto, uma configuração inadequada do ambiente pode permitir acesso indevido ou indisponibilidade do serviço.

3. Diagrama da arquitetura

flowchart TD
    subgraph EXT["Ambiente externo"]
        FRONT["Frontend JSON"]
        RECEP["Recepção / navegador"]
        LAB["Laboratório parceiro"]
    end

    subgraph APP["Ambiente da aplicação"]
        API["FastAPI / APIRouter"]
        CORE["Validação, regras e segurança"]
        DB[("SQLite / SQLModel")]
    end

    FRONT -->|"Requisições JSON"| API
    RECEP -->|"Consulta da agenda"| API
    LAB -->|"Consulta de disponibilidade"| API
    API -->|"Dados validados"| CORE
    CORE -->|"Queries parametrizadas"| DB
    DB -->|"Registros filtrados"| CORE
    CORE -->|"JSON ou HTML escapado"| API

O diagrama apresenta três ambientes principais:

consumidores externos;

aplicação FastAPI;

persistência e operação interna.

A primeira fronteira de segurança ocorre entre os clientes externos e a API. A segunda ocorre entre a aplicação e o banco de dados.

4. Fluxos de dados

F-01 — Frontend para a API

O frontend envia requisições JSON contendo informações como:

identificador do paciente;

identificador do profissional;

data e hora da consulta;

status;

observações.

Principais riscos:

alteração dos identificadores;

envio de campos não previstos;

tentativa de acessar outra consulta;

envio de conteúdo malicioso;

ausência de autenticação.

F-02 — Recepção para a API

O navegador da recepção solicita a agenda de uma determinada data.

A API consulta os registros e retorna uma página HTML.

Principais riscos:

exposição de dados além do necessário;

execução de conteúdo malicioso no navegador;

acesso à agenda sem autorização;

manipulação do parâmetro de data.

F-03 — Laboratório para a API

O laboratório parceiro consulta os horários disponíveis.

Esse fluxo deve retornar somente as informações necessárias para identificar a disponibilidade, sem enviar observações clínicas ou outros dados pessoais.

Principais riscos:

token ou credencial comprometida;

acesso a endpoints que não fazem parte do contrato;

consulta de dados de pacientes;

ausência de rastreabilidade da integração.

F-04 — API para o banco

A camada interna transforma as requisições válidas em operações de leitura ou gravação.

Principais riscos:

consultas SQL construídas de forma insegura;

acesso excessivo ao banco;

uso de credenciais expostas;

persistência de dados inválidos;

alteração de registros sem autorização.

F-05 — Banco para a API

O banco devolve os registros solicitados para a camada da aplicação.

A API deve filtrar esses dados antes de devolvê-los ao cliente. Campos internos ou desnecessários não devem ser expostos.

5. Fronteiras de confiança

TB-01 — Cliente externo e API

É a fronteira entre o frontend, o navegador da recepção, o laboratório e a aplicação.

Riscos principais:

requisições falsificadas;

parâmetros alterados;

tentativa de enumeração de identificadores;

payloads maliciosos;

abuso de requisições.

Controles necessários:

autenticação;

autorização por papel;

verificação de ownership;

validação de entrada;

mensagens de erro genéricas;

limitação de requisições;

comunicação protegida.

TB-02 — API e camada interna

É a fronteira entre as rotas HTTP e a lógica interna da aplicação.

Riscos principais:

rotas implementando regras diferentes;

ausência de validação;

duplicação de controles de segurança;

acesso direto à persistência;

retorno de campos internos.

Controles necessários:

dependências centralizadas;

modelos Pydantic;

modelos específicos para resposta;

separação entre rotas, regras e banco;

tratamento uniforme de erros.

TB-03 — Aplicação e banco de dados

É a fronteira entre o processo da API e a persistência.

Riscos principais:

SQL Injection;

credenciais expostas;

acesso excessivo;

alteração não autorizada;

vazamento de informações em erros.

Controles necessários:

SQLModel;

queries parametrizadas;

sessões controladas;

usuário do banco com menor privilégio;

configuração por variáveis de ambiente;

backups protegidos.

TB-04 — API e integração externa

É a fronteira específica do laboratório parceiro.

Riscos principais:

credencial reutilizada;

token sem expiração;

escopo amplo;

acesso a dados além do necessário;

impossibilidade de identificar o sistema responsável pela chamada.

Controles necessários:

credencial exclusiva;

escopos limitados;

expiração e rotação de tokens;

respostas minimizadas;

registro das requisições.

6. Vetores de ataque no eixo de design

6.1 Endpoint com responsabilidade ampla

Quando uma rota realiza validação, autorização, regra de negócio e acesso ao banco ao mesmo tempo, aumenta o risco de inconsistência e bypass de controles.

Impacto:

regras diferentes entre endpoints;

dificuldade de auditoria;

duplicação de segurança;

falhas não percebidas em novas rotas.

Controle recomendado:

separar rotas, modelos, regras de segurança e persistência;

centralizar verificações comuns;

aplicar o princípio da responsabilidade única.

6.2 Broken Object Level Authorization

Uma rota que recebe apenas o identificador da consulta pode permitir que um usuário troque esse identificador e acesse outro registro.

Impacto:

exposição de dados de pacientes;

alteração indevida de consultas;

violação de confidencialidade e integridade.

Controle recomendado:

verificar a identidade do usuário;

verificar o papel do usuário;

confirmar se o usuário pode acessar aquele objeto específico;

retornar resposta genérica quando o objeto não puder ser acessado.

6.3 Exposição excessiva de dados

Retornar todos os campos armazenados no banco aumenta a possibilidade de vazamento de informações internas.

Controle recomendado:

usar modelos de resposta específicos;

retornar somente os campos necessários;

separar respostas para frontend, recepção e laboratório.

6.4 Integração externa com privilégio excessivo

O laboratório não deve possuir acesso equivalente ao de um administrador ou profissional de saúde.

Controle recomendado:

definir operações específicas;

limitar escopos;

impedir acesso a pacientes e observações;

aplicar o princípio do menor privilégio.

7. Vetores de ataque no eixo de implementação

7.1 Validação insuficiente

Entradas sem validação podem conter identificadores inválidos, datas incorretas, valores inesperados ou campos adicionais.

Controle recomendado:

utilizar tipos explícitos;

validar UUIDs, datas e status;

aplicar limites de tamanho;

rejeitar campos desconhecidos com extra="forbid" quando aplicável.

7.2 SQL Injection

A montagem de comandos por concatenação de strings pode permitir que o conteúdo enviado pelo usuário altere a consulta.

Controle observado:

utilização de SQLModel;

consultas estruturadas;

ausência de concatenação manual de SQL.

Esse controle deve ser mantido em todas as novas consultas.

7.3 Cross-Site Scripting

Observações de uma consulta podem conter conteúdo HTML ou JavaScript malicioso.

Controle observado:

utilização de Jinja2;

escape automático das variáveis exibidas no template.

Cuidados necessários:

não usar |safe em dados não confiáveis;

não inserir valores diretamente em scripts;

validar e limitar textos recebidos;

evitar exibir informações desnecessárias no HTML.

7.4 Bypass de dependências de segurança

Se cada rota implementa sua própria autenticação ou autorização, uma rota nova pode esquecer uma verificação importante.

Controle recomendado:

centralizar as dependências de segurança;

aplicar a dependência diretamente às rotas protegidas;

testar tanto acessos permitidos quanto negados.

7.5 Excesso de dados no payload

Payloads muito grandes podem aumentar o consumo de recursos ou permitir a inclusão de informações não previstas.

Controle recomendado:

limitar tamanho dos campos;

rejeitar propriedades desconhecidas;

aceitar somente os campos definidos no contrato;

evitar armazenar conteúdo sem finalidade definida.

7.6 Exposição de informações em erros

Stack traces, nomes de tabelas, caminhos de arquivos e detalhes de conexão não devem ser enviados ao cliente.

Controle recomendado:

tratar exceções;

retornar mensagens genéricas;

registrar detalhes apenas em logs protegidos;

evitar incluir dados pessoais nos logs.

8. Vetores de ataque no eixo de infraestrutura

8.1 Comunicação sem proteção

O uso de HTTP sem TLS em ambiente produtivo pode permitir interceptação de credenciais e dados de saúde.

Controle recomendado:

utilizar HTTPS;

proteger certificados;

redirecionar HTTP para HTTPS;

impedir o envio de tokens em URLs.

8.2 Exposição da documentação e portas

A documentação /docs e portas de desenvolvimento podem revelar informações sobre endpoints, modelos e parâmetros.

Controle recomendado:

revisar a exposição da documentação;

restringir acesso em produção;

não disponibilizar o servidor de desenvolvimento publicamente;

manter somente as portas necessárias abertas.

8.3 CORS permissivo

Uma configuração ampla de CORS pode permitir que origens não autorizadas façam requisições ao serviço.

Controle recomendado:

utilizar uma allowlist explícita;

evitar allow_origins=["*"] em rotas protegidas;

revisar origens autorizadas periodicamente.

8.4 Ausência de cabeçalhos de segurança

A falta de cabeçalhos HTTP pode aumentar riscos de clickjacking, MIME sniffing e carregamento indevido de conteúdo.

Controles recomendados:

Strict-Transport-Security;

X-Frame-Options;

X-Content-Type-Options;

política de conteúdo adequada;

política de referrer compatível com o sistema.

8.5 Ausência de proteção contra abuso

Sem limites de requisição, um atacante pode consumir recursos da API ou tentar várias credenciais.

Controle recomendado:

rate limiting;

limites específicos para rotas sensíveis;

bloqueio progressivo;

monitoramento de padrões anormais;

alertas para excesso de erros.

8.6 Banco local sem estratégia operacional

O SQLite é adequado para desenvolvimento e testes, mas pode exigir cuidados adicionais em ambientes com concorrência, backup e disponibilidade maiores.

Controle recomendado:

controlar permissões do arquivo;

proteger backups;

testar restauração;

monitorar falhas;

avaliar o banco adequado ao ambiente de produção.

9. Priorização dos vetores

A prioridade dos riscos foi definida considerando a sensibilidade dos dados:

Prioridade crítica

BOLA;

acesso sem autenticação;

exposição excessiva de dados de pacientes;

credenciais ou tokens expostos;

acesso indevido pela integração externa.

Prioridade alta

SQL Injection;

XSS armazenado;

CORS permissivo;

ausência de HTTPS;

falta de controle de alterações;

ausência de rate limiting.

Prioridade média

exposição da documentação;

mensagens de erro detalhadas;

ausência de monitoramento;

configurações inseguras do banco local;

ausência de política formal de backup.

10. Validação crítica

A arquitetura mostra que a segurança não depende apenas do código das rotas.

Mesmo com SQLModel e Jinja2 configurados corretamente:

a aplicação ainda pode sofrer BOLA se não verificar ownership;

um modelo de resposta não impede que uma pessoa não autorizada alcance o endpoint;

um token válido pode ser perigoso se possuir permissões excessivas;

HTTPS não corrige falhas de autorização;

CORS não substitui autenticação;

esconder a documentação não protege uma rota vulnerável;

o banco parametrizado não impede alterações feitas por usuários autorizados de forma indevida.

Por isso, os controles devem ser aplicados em conjunto nos três eixos analisados.

11. Conclusão

A arquitetura foi dividida em clientes externos, camada HTTP/API, validação e segurança, persistência e operação.

As principais fronteiras de confiança estão entre os consumidores externos e a API, entre a API e a camada interna, entre a aplicação e o banco de dados e entre a API e o laboratório parceiro.

Os riscos mais importantes são BOLA, exposição excessiva de dados, autenticação insuficiente, integração externa com privilégios amplos, XSS, SQL Injection, CORS permissivo, ausência de HTTPS e falta de proteção contra abuso.

A separação das partições permite aplicar controles específicos em cada camada, reduzindo a duplicação de lógica e facilitando a revisão de segurança da aplicação.