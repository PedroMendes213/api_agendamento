## 1. Objetivo

Este exercício apresenta uma análise manual de segurança da API de agendamento de consultas médicas.

A aplicação utiliza FastAPI, SQLModel, JWT, OAuth 2.0 para integração M2M e separação modular entre rotas, modelos, banco de dados e autenticação.

A análise foi feita considerando:

- a evolução do código desenvolvido neste projeto;
- as vulnerabilidades tratadas nos exercícios anteriores;
- os padrões vulneráveis apresentados no repositório de referência fornecido pelo professor.

O repositório de referência foi utilizado somente para orientar a análise de segurança. Nenhum código foi copiado para substituir a implementação atual da aplicação.

## 2. Critério de análise

Foram procurados problemas relacionados a:

- controle de acesso;
- autenticação e autorização;
- proteção de informações sensíveis;
- regras de negócio;
- configuração criptográfica;
- registro e monitoramento de eventos.

A análise também verificou se as consultas ao banco de dados utilizam parâmetros e se existe concatenação insegura de SQL.

## 3. Vulnerabilidade 1 — A01: Broken Access Control / BOLA

### Descrição

BOLA, ou Broken Object Level Authorization, ocorre quando a aplicação verifica apenas se o usuário está autenticado, mas não verifica se ele possui autorização para acessar aquele objeto específico.

Em uma API de consultas médicas, um exemplo de BOLA seria:

1. um profissional autenticado acessa uma consulta própria;
2. o identificador da consulta é alterado na URL;
3. a aplicação retorna uma consulta pertencente a outro profissional ou paciente.

Esse problema é especialmente grave porque consultas médicas podem conter dados pessoais e informações relacionadas à saúde.

### Padrão vulnerável identificado

O padrão vulnerável consiste em buscar uma consulta somente pelo identificador:

```python
consulta = session.get(Consulta, consulta_id)

if consulta is None:
    raise HTTPException(status_code=404)

return consulta
```

Nesse padrão, não existe validação para confirmar se o usuário autenticado está relacionado à consulta.

O mesmo problema aparece na base de referência quando os registros são buscados com `select(...).all()` sem aplicar filtro de propriedade ou relacionamento com o usuário autenticado.

### Impacto

Um usuário autenticado poderia acessar dados de terceiros alterando um UUID ou outro identificador da URL.

Os impactos incluem:

- exposição de dados pessoais;
- exposição de informações médicas;
- violação do princípio do menor privilégio;
- risco de violação da LGPD;
- acesso indevido a informações de pacientes.

### Severidade

**Crítica.**

A vulnerabilidade permite acesso indevido a informações sensíveis de saúde.

### Tratamento aplicado na aplicação atual

Na implementação atual, a autorização foi centralizada na camada de autenticação e autorização.

As rotas de consultas utilizam verificações de ownership, como:

- `garantir_leitura_consulta`;
- `garantir_gerenciamento_consulta`;
- `garantir_profissional_da_consulta`.

Além disso, a listagem de consultas de um profissional é filtrada pelo `profissional_id` associado ao token autenticado.

Dessa forma, a aplicação não depende somente do identificador enviado pelo cliente. Ela também verifica a relação entre o usuário autenticado e o recurso solicitado.

O acesso indevido deve retornar:

```text
HTTP 403 Forbidden
```

Esse comportamento foi validado anteriormente no teste de ownership da aplicação.

## 4. Vulnerabilidade 2 — A02: Cryptographic Failures

### Descrição

A aplicação utiliza JWT para autenticação. Portanto, a chave usada para assinar os tokens precisa ser protegida e diferente entre os ambientes.

Uma configuração insegura ocorre quando a aplicação possui uma chave secreta previsível ou fixa no código, por exemplo:

```python
jwt_secret_key = "development-only-change-this-secret-key"
```

Se essa chave for utilizada em produção, um atacante que descubra o valor poderá criar tokens falsos.

### Impacto

Um token forjado poderia conter:

- papel de administrador;
- identidade de outro usuário;
- escopos M2M indevidos;
- permissões para acessar informações protegidas.

Isso poderia comprometer todos os mecanismos de autorização baseados em JWT.

### Severidade

**Alta ou crítica**, dependendo do ambiente.

Em produção, o comprometimento da chave pode permitir a falsificação de qualquer token da aplicação.

### Tratamento recomendado

A chave deve ser carregada por variável de ambiente ou por um gerenciador de segredos.

O arquivo `.env.example` deve conter apenas um exemplo sem valor real:

```env
JWT_SECRET_KEY=defina-uma-chave-segura-fora-do-repositorio
```

O arquivo `.env` real não deve ser versionado nem incluído no pacote final.

Também é necessário:

- gerar uma chave longa e aleatória;
- utilizar chaves diferentes para desenvolvimento, testes e produção;
- invalidar tokens quando houver troca emergencial da chave;
- nunca registrar tokens ou segredos nos logs;
- não incluir client secrets reais nas evidências ou no relatório.

## 5. Vulnerabilidade 3 — A04: Insecure Design

### Descrição

A regra de negócio deve impedir que dois agendamentos incompatíveis sejam criados para o mesmo profissional no mesmo horário.

Se a aplicação apenas grava a consulta sem verificar conflitos, duas requisições simultâneas podem reservar o mesmo horário.

Esse problema não é resolvido apenas com autenticação, pois usuários autorizados também podem executar operações conflitantes.

### Padrão vulnerável

O padrão vulnerável é criar uma consulta diretamente:

```python
consulta = Consulta(**dados.model_dump())
session.add(consulta)
session.commit()
```

sem verificar se já existe outra consulta ativa para:

- o mesmo profissional;
- a mesma data e hora;
- um status que represente agendamento válido.

### Impacto

A ausência dessa regra pode causar:

- dupla marcação;
- conflitos na agenda;
- atendimento simultâneo de pacientes;
- inconsistência entre a agenda da recepção e a agenda do profissional;
- falhas de confiabilidade do sistema.

### Severidade

**Alta.**

O problema afeta diretamente a operação das clínicas e a integridade dos agendamentos.

### Tratamento recomendado

Antes de inserir uma consulta, a aplicação deve executar uma consulta parametrizada verificando o mesmo profissional e horário.

Também é recomendado criar uma restrição de unicidade no banco de dados para reforçar a regra contra condições de corrida.

A regra deve considerar somente consultas ativas, permitindo que horários de consultas canceladas sejam reutilizados quando essa for a regra definida pelo negócio.

## 6. Vulnerabilidade 4 — A07: Identification and Authentication Failures

### Descrição

Um risco comum ocorre quando uma rota pública de cadastro permite que o cliente envie diretamente o próprio papel de acesso.

Por exemplo, um cadastro público que aceite o campo abaixo pode permitir escalada de privilégio:

```json
{
  "username": "usuario",
  "senha": "senha-segura",
  "papel": "administrador"
}
```

O cliente não deve escolher livremente seu papel de autorização.

### Impacto

Um atacante poderia criar uma conta com privilégios administrativos e acessar operações protegidas.

Os impactos incluem:

- criação de outros usuários;
- alteração de permissões;
- acesso a dados de pacientes;
- criação de clientes M2M;
- emissão de tokens com privilégios elevados.

### Severidade

**Crítica.**

A criação indevida de uma conta administrativa compromete o controle de toda a API.

### Tratamento aplicado na aplicação atual

A criação administrativa de usuários está protegida pela exigência do papel de administrador.

A rota utiliza uma dependência equivalente a:

```python
exigir_papeis(Papel.ADMINISTRADOR)
```

Além disso, o modelo de entrada aplica validação explícita e não deve aceitar campos desconhecidos.

O papel do novo usuário deve ser validado pelo servidor, e não confiado diretamente ao cliente.

## 7. Vulnerabilidade 5 — A09: Security Logging and Monitoring Failures

### Descrição

A aplicação manipula informações sensíveis, mas precisa manter uma trilha de auditoria suficiente para detectar e investigar eventos de segurança.

Não basta apenas retornar `401` ou `403`. Também é importante registrar eventos relevantes sem armazenar dados sensíveis desnecessários.

### Eventos que devem ser auditados

A aplicação deve considerar o registro de:

- tentativas de login malsucedidas;
- tokens inválidos ou expirados;
- acessos negados por falta de ownership;
- criação e alteração de consultas;
- exclusão e cancelamento de consultas;
- criação de usuários administrativos;
- criação e utilização de clientes M2M;
- tentativas de utilização de escopos não autorizados.

### Cuidados com os registros

Os logs não devem armazenar:

- senhas;
- client secrets;
- tokens JWT completos;
- dados médicos desnecessários;
- informações pessoais além do necessário para auditoria.

Os eventos devem utilizar identificadores técnicos, data, operação, resultado e, quando apropriado, o identificador do usuário.

### Impacto

Sem uma trilha de auditoria adequada, torna-se mais difícil:

- investigar acessos indevidos;
- identificar abuso de permissões;
- detectar comprometimento de tokens;
- comprovar o tratamento de incidentes;
- demonstrar governança sobre dados pessoais.

### Severidade

**Média a alta**, dependendo da ausência de monitoramento no ambiente de produção.

## 8. Verificação de SQL Injection

Durante a análise, não foi identificado uso de concatenação de strings para formar consultas SQL.

As consultas da aplicação utilizam SQLModel e expressões parametrizadas, por exemplo:

```python
select(Consulta).where(
    Consulta.profissional_id == profissional_id
)
```

Esse padrão é preferível à montagem manual de SQL com valores recebidos do cliente.

Exemplo inseguro que não deve ser utilizado:

```python
query = f"SELECT * FROM consultas WHERE id = '{consulta_id}'"
```

A aplicação deve continuar utilizando consultas parametrizadas em todas as rotas.

## 9. Resumo dos achados

| Categoria | Vulnerabilidade | Situação |
|---|---|---|
| A01 | BOLA e ausência de ownership | Tratada nas rotas atuais |
| A02 | Chave JWT previsível ou padrão | Deve ser protegida por configuração segura |
| A04 | Ausência de prevenção contra conflito de horários | Regra de negócio deve ser reforçada |
| A07 | Cadastro permitindo escolha indevida de papel | Tratada com rota administrativa protegida |
| A09 | Ausência de trilha de auditoria suficiente | Deve ser implementada e monitorada |

## 10. Conclusão

A análise identificou vulnerabilidades de categorias distintas do OWASP Top 10.

A falha mais grave é a BOLA, pois pode permitir que um usuário autenticado acesse uma consulta ou informação pertencente a outra pessoa. Por esse motivo, a aplicação atual utiliza verificações de ownership antes de retornar, alterar ou excluir consultas.

Também foram identificados riscos relacionados à proteção da chave JWT, à ausência de validação de conflito de horários, à atribuição indevida de papéis e à falta de auditoria detalhada.

A análise demonstra que autenticar o usuário não é suficiente. Cada operação deve verificar:

1. quem é o usuário;
2. qual é o papel do usuário;
3. qual é o escopo da operação;
4. qual é a relação do usuário com o recurso;
5. se a operação respeita as regras de negócio;
6. se o evento pode ser auditado posteriormente.