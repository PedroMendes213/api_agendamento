## 1. Objetivo

Este exercício implementa controles de segurança relacionados à comunicação HTTP, origens autorizadas e proteção contra abuso do endpoint de autenticação.

Foram implementados:

- CORS com allowlist explícita;
- cabeçalho HSTS;
- cabeçalho X-Frame-Options;
- cabeçalho X-Content-Type-Options;
- rate limiting específico para o endpoint `/auth/token`;
- testes automatizados para validar os controles.

## 2. Configuração CORS

A aplicação utiliza uma allowlist explícita de origens permitidas:

```text
http://localhost:3000
http://127.0.0.1:3000
```

A configuração não utiliza wildcard:

```text
CORS_ALLOWED_ORIGINS=*
```

A opção `allow_credentials` foi mantida como `False`, pois a aplicação utiliza o cabeçalho `Authorization` com Bearer Token e não depende de cookies de sessão.

Os métodos e cabeçalhos permitidos também foram definidos explicitamente:

```python
allow_methods=[
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "OPTIONS",
]

allow_headers=[
    "Authorization",
    "Content-Type",
]
```

Essa configuração reduz a superfície de exposição da API para aplicações frontend não autorizadas.

Uma origem permitida recebe o cabeçalho:

```text
Access-Control-Allow-Origin: http://localhost:3000
```

Uma origem que não está na allowlist não recebe autorização CORS.

## 3. Cabeçalhos de segurança HTTP

Foi criado um middleware centralizado para adicionar cabeçalhos de segurança às respostas.

### HSTS

Foi configurado:

```text
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

Esse cabeçalho orienta o navegador a utilizar HTTPS durante o período configurado.

Em produção, o serviço deve ser publicado atrás de HTTPS válido antes da ativação definitiva do HSTS.

### X-Frame-Options

Foi configurado:

```text
X-Frame-Options: DENY
```

Esse cabeçalho impede que as páginas da aplicação sejam carregadas dentro de `iframe`, reduzindo o risco de clickjacking.

### X-Content-Type-Options

Foi configurado:

```text
X-Content-Type-Options: nosniff
```

Esse cabeçalho impede que o navegador tente interpretar o conteúdo como outro tipo diferente do declarado pelo servidor.

## 4. Rate limiting do login

O endpoint abaixo recebeu uma limitação específica:

```text
POST /auth/token
```

A regra aplicada é:

```text
5 tentativas por endereço IP a cada 60 segundos
```

O contador é incrementado antes da validação da senha, portanto tentativas com credenciais inválidas também são contabilizadas.

Quando o limite é ultrapassado, a aplicação retorna:

```text
HTTP 429 Too Many Requests
```

Resposta esperada:

```json
{
  "detail": "Muitas tentativas de login. Aguarde antes de tentar novamente."
}
```

Também são enviados os cabeçalhos:

```text
Retry-After
X-RateLimit-Limit
X-RateLimit-Remaining
```

O cabeçalho `Retry-After` informa ao cliente quantos segundos deve aguardar antes de tentar novamente.

## 5. Escolha da implementação

O rate limiter foi centralizado em:

```text
app/security.py
```

A implementação utiliza uma janela deslizante em memória e bloqueio por endereço IP.

Essa solução é adequada para o ambiente local e para uma execução única da aplicação. Em uma implantação com múltiplos processos ou múltiplos servidores, o armazenamento do contador deve ser substituído por uma solução compartilhada, como Redis, para que todos os processos utilizem o mesmo limite.

## 6. Testes realizados

Foram criados testes automatizados para validar:

- origem CORS permitida;
- origem CORS não autorizada;
- presença do HSTS;
- presença do X-Frame-Options;
- presença do X-Content-Type-Options;
- bloqueio após cinco tentativas de login;
- retorno HTTP 429;
- presença do cabeçalho Retry-After;
- presença dos cabeçalhos de limite.

O arquivo dos testes é:

```text
tests/test_exercicio10.py
```

O resultado esperado é:

```text
16 passed
```

## 7. Evidências

As evidências utilizadas são:

```text
ex10_01_pytest_12_passed_cors_headers.png
ex10_02_pytest_12_passed_rate_limit.png
ex10_03_pytest_16_passed_rede_rate_limit.png
```

O primeiro print demonstra que a configuração de CORS e dos cabeçalhos não quebrou os testes anteriores.

O segundo print demonstra que a implementação inicial do rate limiting foi integrada sem regressões.

O terceiro print demonstra a aprovação dos testes específicos de rede e proteção contra abuso.

## 8. Conclusão

A API passou a aceitar somente origens frontend previamente autorizadas e deixou de utilizar CORS com wildcard.

Também foram adicionados cabeçalhos HTTP básicos contra:

- transporte inseguro;
- clickjacking;
- interpretação incorreta do tipo de conteúdo.

O endpoint de autenticação recebeu um limite específico contra tentativas repetidas, reduzindo o risco de ataques de força bruta.

Os controles foram implementados de forma centralizada para que novas rotas também possam utilizar a mesma estrutura de segurança.