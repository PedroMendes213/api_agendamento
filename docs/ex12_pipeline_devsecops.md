## 1. Objetivo

Foi criado um pipeline DevSecOps para executar testes automatizados, análise estática do código, auditoria de dependências, análise dinâmica da aplicação e testes interativos de segurança.

O pipeline está definido em:

```text
.github/workflows/security.yml

A política de bloqueio está centralizada em:
scripts/security_gate.py

Os testes de segurança derivados do threat model estão em:
tests/test_exercicio12.py

2. Estratégia no ciclo de desenvolvimento
Análise estática — SAST
A ferramenta Bandit é executada depois do checkout do código e antes da aprovação do pipeline.
Essa etapa procura padrões inseguros diretamente no código Python, como uso perigoso de funções, problemas de configuração e práticas que podem gerar vulnerabilidades.
A análise estática foi posicionada no início do pipeline porque não precisa executar a aplicação e fornece retorno rápido ao desenvolvedor.
O comando utilizado é:
bandit -r app -f json -o artifacts/bandit.json --exit-zero

Depois da análise, o relatório é avaliado pelo security gate personalizado.
Análise de dependências — SCA
A ferramenta pip-audit verifica as bibliotecas declaradas no arquivo requirements.txt.
Essa etapa identifica dependências com vulnerabilidades públicas conhecidas e foi posicionada antes da análise dinâmica, pois também não depende da aplicação estar em execução.
O comando utilizado é:
pip-audit -r requirements.txt --format=json --output=artifacts/pip-audit.json

Testes interativos de segurança
A suíte Pytest utiliza o TestClient do FastAPI para exercitar a aplicação em tempo de execução.
Foram incluídos testes para:
- rejeição de acesso sem JWT;
- rejeição de JWT malformado;
- bloqueio de tentativa de injeção sem autenticação;
- rejeição de origem CORS não autorizada.
Essa etapa verifica o comportamento real dos controles de segurança e complementa a análise estática.
Análise dinâmica — DAST
O OWASP ZAP é executado depois que a aplicação é iniciada em um servidor temporário no pipeline.
A ferramenta acessa a API em execução e procura problemas observáveis externamente, como exposição indevida de rotas, cabeçalhos ausentes e configurações inseguras.
O relatório gerado pelo ZAP é armazenado como artefato do GitHub Actions.
3. Vulnerabilidades priorizadas
BOLA — Broken Object Level Authorization
- CVSS: 8.1 — Alto.
- Vetor considerado: AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N.
- Impacto de negócio: crítico.
- Consequência: exposição ou alteração de dados de saúde de outro paciente.
- Tratamento: verificação centralizada de ownership no JWT e na consulta ao banco.
- Critério: bloqueia o pipeline quando identificado como vulnerabilidade High ou Critical.
SQL Injection
- CVSS: 9.8 — Crítico.
- Vetor considerado: AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H.
- Impacto de negócio: crítico.
- Consequência: leitura, alteração ou exclusão de dados clínicos.
- Tratamento: uso de SQLModel com expressões parametrizadas e validação de entrada.
- Critério: bloqueia o pipeline.
Uso de segredo JWT fraco ou padrão
- CVSS: 9.8 — Crítico.
- Impacto de negócio: crítico.
- Consequência: falsificação de tokens e acesso indevido às funções da API.
- Tratamento: segredo carregado pelo BaseSettings, armazenado no .env local e nunca versionado.
- Critério: bloqueia o pipeline.
XSS armazenado
- CVSS: 6.1 — Médio.
- Vetor considerado: AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N.
- Impacto de negócio: alto, pois a página HTML pode ser utilizada pela recepção.
- Consequência: execução de código JavaScript no navegador de outro usuário.
- Tratamento: autoescape do Jinja2 e validação de entrada.
- Critério: o achado é registrado para correção; o gate automático bloqueia quando a ferramenta o classificar como High ou Critical.
Ataques de força bruta no login
- CVSS: 7.5 — Alto.
- Impacto de negócio: alto.
- Consequência: comprometimento de contas e acesso a dados protegidos.
- Tratamento: rate limiting diferenciado no endpoint de login.
- Critério: bloqueia o pipeline quando classificado como High ou Critical.
CORS excessivamente permissivo
- CVSS: 6.5 — Médio.
- Impacto de negócio: médio/alto.
- Consequência: acesso indevido à API por origens não autorizadas.
- Tratamento: allowlist explícita de origens e rejeição de origens desconhecidas.
- Critério: é monitorado pelo teste automatizado e pelo DAST.
4. Critério do security gate
O pipeline bloqueia quando ocorre qualquer uma das situações abaixo:
1. Algum teste automatizado falha.
2. O Bandit identifica uma vulnerabilidade High.
3. O pip-audit identifica dependência vulnerável com CVSS igual ou superior a 7.0.
4. Uma vulnerabilidade de dependência é encontrada sem score verificável.
5. O OWASP ZAP identifica alerta High ou Critical.
6. Qualquer etapa obrigatória do pipeline termina com erro.
O limite de bloqueio adotado foi CVSS 7.0 porque vulnerabilidades nesse nível representam risco alto para uma aplicação que processa dados pessoais e informações de saúde.
Vulnerabilidades Medium e Low continuam registradas nos relatórios e devem ser corrigidas no ciclo de desenvolvimento, mas não interrompem automaticamente o pipeline.
5. Organização do pipeline
O fluxo executado pelo GitHub Actions é:
1. Checkout do código.
2. Instalação das dependências.
3. Execução dos testes funcionais.
4. Execução dos testes interativos de segurança.
5. Análise SAST com Bandit.
6. Análise SCA com pip-audit.
7. Inicialização temporária da API.
8. Análise DAST com OWASP ZAP.
9. Avaliação dos relatórios pelo security gate.
10. Aprovação ou bloqueio final do pipeline.
Os relatórios são publicados como artefatos do GitHub Actions para permitir auditoria posterior.
6. Segurança das credenciais
O workflow gera um segredo JWT temporário durante a execução do CI.
Nenhum segredo real é gravado no código-fonte, no workflow ou no pacote de entrega.
A configuração local utiliza o arquivo .env, que deve permanecer fora do versionamento. O arquivo entregue ao avaliador deve ser somente:
.env.example

sem credenciais reais.
7. Evidências
As evidências previstas para este exercício são:
ex12_01_pytest_4_passed_threat_model.png
ex12_02_github_actions_security_gate_aprovado.png
ex12_03_relatorio_zap_artifact.png

A primeira evidência comprova os testes de segurança locais.
A segunda comprova a execução bem-sucedida do pipeline no GitHub Actions.
A terceira comprova a geração do relatório do OWASP ZAP como artefato do pipeline.