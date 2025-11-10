# TestSprite AI Testing Report (Consolidado)

## Metadados
- Projeto: `whago`
- Data: 2025-11-09
- Preparado por: TestSprite + GPT-5 Codex

## Visão Geral dos Resultados
- Testes executados: 19
- Aprovados: 4
- Reprovados: 15
- Fail rate: **78,9 %**
- Tendência: o sistema passou em validações básicas (login, refresh de token, monitoramento de chips, verificação de hashing), mas grande parte dos fluxos críticos está bloqueada por ausência de telas, falhas de UI (botões inativos), falta de dados seed ou recursos indisponíveis para o plano atual.

## Cobertura por Requisito

### Requisito R1 – Autenticação e Registro
| ID | Caso | Resultado | Observações |
|----|------|-----------|-------------|
| TC001 | Registro com dados válidos | ❌ | Formulário de registro não acessível na navegação atual. |
| TC002 | Registro com email inválido | ❌ | Mesmo bloqueio do caso anterior. |
| TC003 | Login com credenciais válidas | ✅ | Fluxo concluído; tokens armazenados corretamente. |
| TC004 | Login com credenciais inválidas | ❌ | Botão de logout inoperante impede retorno à tela de login. |
| TC005 | Expiração e refresh de JWT | ✅ | Expiração simulada e refresh funcionaram. |

### Requisito R2 – Gestão de Chips
| ID | Caso | Resultado | Observações |
|----|------|-----------|-------------|
| TC006 | Adicionar chip (limite do plano) | ❌ | Usuário seed está no plano Free e logout falha; impossível testar plano Business. |
| TC007 | Monitoramento em tempo real | ✅ | Painel reflete estados dos chips existentes. |
| TC008 | Maturação automática | ❌ | Nenhum chip conectado; ausência de controles de start. |
| TC009 | Rotação automática | ❌ | Botão `Nova campanha` não abre wizard para configurar rotação. |

### Requisito R3 – Campanhas e Mensagens
| ID | Caso | Resultado | Observações |
|----|------|-----------|-------------|
| TC010 | Criação completa de campanha | ❌ | Botão `Nova campanha` não responde. |
| TC011 | Ciclo de vida da campanha | ❌ | Não há campanhas; bloqueado pela criação. |
| TC012 | Limites e intervalos por plano | ❌ | Mesma causa: criação de campanha indisponível. |

### Requisito R4 – Relatórios, Notificações e Integrações
| ID | Caso | Resultado | Observações |
|----|------|-----------|-------------|
| TC013 | Relatórios multi-formato | ❌ | Exports de campanhas funcionam; chips falha em CSV/XLSX; relatório financeiro falha em PDF. |
| TC014 | Notificações in-app/email | ❌ | Botão `Comprar créditos` não altera saldo; eventos não disparam notificações. |
| TC015 | Webhooks (ENTERPRISE) | ❌ | Seção de configuração não existe na UI atual. |

### Requisito R5 – APIs, Segurança e UX
| ID | Caso | Resultado | Observações |
|----|------|-----------|-------------|
| TC016 | API Key + rate limiting | ❌ | Nenhuma interface/API key disponível para testes. |
| TC017 | Segurança / criptografia em repouso | ✅ | Registro confirma armazenamento criptografado. |
| TC018 | Responsividade e acessibilidade | ❌ | Validado apenas em desktop; mobile/teclado/screen reader não cobertos. |
| TC019 | Estados de loading / sucesso / erro | ❌ | Botão `Nova campanha` sem feedback ou operação, bloqueando verificação. |

## Análise Detalhada das Falhas
- **Lacuna de navegação**: não existe rota visível para `/register`; cadastro fica inacessível. Impacta onboarding e testes TC001/TC002.
- **Logout quebrado**: botão `Sair` não reage; impede simular outros perfis (Business/Enterprise) e validar fluxo de login inválido.
- **Dados e controles ausentes**:
  - Nenhum chip conectado/acionável → maturação e rotação não podem ser exercitados.
  - Wizard de campanhas não abre (`Nova campanha` sem handler) → bloqueia todo o conjunto de testes de campanhas e mensagens, além de feedback visual (TC009–TC012, TC019).
  - Compras de créditos não afetam saldo → impossibilita cenários de notificações.
  - Configuração de webhooks e API keys não existe na UI → requisitos Enterprise não atendidos.
- **Exportações inconsistentes**: CSV/XLSX de relatório de chips e PDF de relatório financeiro falham; apenas parte dos formatos funciona.
- **Cobertura parcial de UX**: Teste de responsividade não consegue validar tamanhos mobile/tablet nem acessibilidade via teclado/ARIA.

## Recomendações
1. **Restaurar links de registro e logout** para permitir criação de contas e troca de usuário nos testes automatizados.
2. **Criar seed ou mock para dados críticos** (chips conectados, campanhas de exemplo, créditos variando). Há utilitários em `frontend-tests/utils/db.ts` que podem ser adaptados.
3. **Revisar actions de UI**:
   - Implementar comportamento do botão `Nova campanha`.
   - Garantir que `Comprar créditos` atualiza saldo e dispara eventos.
4. **Expor painéis Enterprise** (webhook, API key) mesmo que em modo demo, ou ajustar plano do usuário padrão.
5. **Padronizar exports de relatórios** assegurando downloads para todos os formatos prometidos.
6. **Ampliar cobertura de UX** com testes viewport mobile/tablet e navegação por teclado.

## Próximos Passos
- Corrigir os bloqueadores de UI e disponibilizar dados de teste mínimos.
- Reexecutar a suíte do Testsprite para capturar novas evidências após os ajustes.
- Complementar com testes Playwright e2e já existentes em `frontend-tests/e2e` para validar fluxos específicos.
# TestSprite AI Testing Report (MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** whago
- **Date:** 2025-11-09
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

### Requirement R1 – Autenticação e Sessões
- **Objetivo:** Garantir registro, login e renovação de sessão confiáveis para usuários finais.

#### Test TC001 – User Registration with Valid Data
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** O fluxo não respondeu dentro da janela de 15 minutos. Indica que o endpoint `/api/v1/auth/register` não concluiu ou não estava acessível durante o teste automatizado. Verificar disponibilidade do backend e dados seed.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/0a9c56d1-0e54-428e-8549-82400f9e480f

#### Test TC002 – User Registration with Invalid Email
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Mesmo sintoma do TC001. O validador de cadastro não foi exercitado; possível indisponibilidade da rota ou ausência de fixture preparada.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/68ea2520-952c-4d08-a0eb-3211de92af41

#### Test TC003 – User Login with Valid Credentials
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Falha consistente sugere que `/api/v1/auth/login` não retornou resposta. Confirmar que credenciais de teste existem ou que o serviço FastAPI está aceitando conexões externas.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/1c261c13-ca59-4bb6-aacc-68f026e0b73d

#### Test TC004 – User Login with Invalid Credentials
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Mesmo comportamento do TC003. Necessário revisar logs do backend para identificar timeouts ou erros de rede.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/540e52fd-523c-435a-a98a-889144d01528

#### Test TC005 – JWT Token Expiry and Refresh
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Endpoint `/api/v1/auth/refresh` não respondeu a tempo. Confirme se cookies/headers esperados pelo teste estão sendo aceitos e se a instância mantém estado entre chamadas.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/c97af832-6382-41f9-82bb-e57defca48c7

---

### Requirement R2 – Gestão de Chips
- **Objetivo:** Permitir cadastro, monitoramento, maturação e rotação de chips WhatsApp.

#### Test TC006 – Add Chip via QR Code Scan - Business Plan Limit
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** A API de chips não respondeu. Verificar dependências do serviço Baileys ou pré-condições de plano.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/bddcba2c-2e2e-40a1-85ee-91f82bc0bb06

#### Test TC007 – Chip Status Monitoring Real-Time
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Falta de resposta sugere que o websocket ou endpoint REST associado não está acessível. Confirmar configuração de Redis e autenticação WS.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/63084e83-1cc0-49e8-aabd-4e4b396fb53a

#### Test TC008 – Chip Maturation Automatic Heat-up Process (BUSINESS/ENTERPRISE)
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Processo assíncrono não foi exercitado; sem resposta da API. Avaliar se workers Celery estavam ativos durante o teste.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/939a90fb-7ec5-4c84-9981-909973660a24

#### Test TC009 – Chip Rotation Automatic Distribution
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Timeout consistente. Certificar que parâmetros do teste batem com regras de rotação e que serviços auxiliares (Redis/Celery) estão ativos.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/cec4dfae-2bbd-4dfd-bd8c-b9c65981afb5

---

### Requirement R3 – Campanhas e Envio de Mensagens
- **Objetivo:** Gerenciar ciclo completo de campanhas, envio e limites por plano.

#### Test TC010 – Create Campaign with Contact Import and Message Editor
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Backend não respondeu ao fluxo de criação. Checar se upload de arquivo está habilitado e se há storage configurado.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/b8c0c933-b11b-4148-8554-f50275ed2635

#### Test TC011 – Campaign Lifecycle: Start, Pause, Cancel, Monitor
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Rotas de controle de campanha não responderam. Rever se há filas Celery ativas e se o serviço Baileys está disponível.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/61e8d370-41d7-4594-ab45-2b484cb94e4d

#### Test TC012 – Sending Messages Respecting Plan Limits and Intervals
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Teste não conseguiu validar limites. Possível falta de dados seed ou indisponibilidade de workers responsáveis pelo envio.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/25577730-187f-4e7c-8223-d501c8d9dad5

---

### Requirement R4 – Relatórios, Notificações e Integrações
- **Objetivo:** Disponibilizar relatórios, notificações e integrações externas.

#### Test TC013 – Report Generation with Multiple Export Formats
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Falta de resposta ao requisitar exportações. Revisar geração assíncrona e dependências de arquivos temporários.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/e7eda709-5092-4441-a2c5-7576a91e1895

#### Test TC014 – In-App and Email Notification Delivery
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Notificações não puderam ser verificadas. Checar serviços de e-mail simulados e notificações in-app.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/456adc7a-6e56-4eb3-b618-6eef2d8c740f

#### Test TC015 – Webhook Integration for ENTERPRISE Plan
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Nenhuma resposta obtida. Confirmar configuração de endpoint público exigido pelo teste ou mocks necessários.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/9c5656ab-1c81-4b25-81a9-0c5d5b18c7c5

---

### Requirement R5 – Segurança e Compliance
- **Objetivo:** Garantir controles de segurança, rate limiting e proteção de dados.

#### Test TC016 – API REST Authentication and Rate Limiting
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** API não respondeu. Necessário validar que o ambiente de teste expõe headers corretos e que Redis está operante para rate limiting.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/4ccfcd4e-8c8c-4bd4-9852-628ba94a7681

#### Test TC017 – Data Security and Encryption at Rest
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Falha sugere indisponibilidade do endpoint que deveria comprovar criptografia/sigilo. Investigar se existe rota/documento previsto pelo teste.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/7b7798d7-0a14-420d-a993-02426ce65d42

---

### Requirement R6 – Experiência Frontend
- **Objetivo:** Manter UI responsiva, acessível e com estados visuais consistentes.

#### Test TC018 – Frontend Responsiveness and Accessibility
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Timeout indica que o fluxo E2E não conseguiu carregar a UI. Checar se o frontend está servido e acessível via proxy Testsprite.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/ebe22bc5-2d94-49b1-8c46-01b55cfbcc59

#### Test TC019 – Loading, Success, and Error UI States
- **Resultado:** ❌ Falhou (timeout de 15 minutos)
- **Achados:** Mesma falha do TC018. Validar se assets estáticos estão acessíveis e se o ambiente entrega as rotas necessárias.
- **Link:** https://www.testsprite.com/dashboard/mcp/tests/4a3bf4c0-5c29-4c53-860e-8d4ef9fb3838/8b8552ec-7df1-478f-a14d-a8c690741585

---

## 3️⃣ Coverage & Matching Metrics

- **0.00** of tests passed

| Requirement | Total Tests | ✅ Passou | ❌ Falhou |
|-------------|-------------|-----------|-----------|
| R1 – Autenticação e Sessões | 5 | 0 | 5 |
| R2 – Gestão de Chips | 4 | 0 | 4 |
| R3 – Campanhas e Mensagens | 3 | 0 | 3 |
| R4 – Relatórios, Notificações e Integrações | 3 | 0 | 3 |
| R5 – Segurança e Compliance | 2 | 0 | 2 |
| R6 – Experiência Frontend | 2 | 0 | 2 |

---

## 4️⃣ Principais Lacunas / Riscos
- Timeout generalizado indica que o ambiente exposto ao Testsprite não está respondendo; possível falha na configuração do túnel ou falta de seed/fixtures.
- Dependências externas críticas (Redis, Celery, Baileys, serviço de e-mail) podem não estar ativas durante os testes, bloqueando fluxos assíncronos.
- Ausência de dados de teste e credenciais conhecidas impede validação de autenticação e fluxos downstream.
- Falta de monitoramento/logs compartilhados dificulta diagnóstico rápido; configurar logging remoto ajudará nas próximas execuções.


