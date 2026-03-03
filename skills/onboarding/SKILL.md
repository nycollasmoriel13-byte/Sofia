# Skill: Onboarding

## Objetivo
Coletar todos os dados tecnicos necessarios para configurar o bot do cliente apos o pagamento, sem precisar de contato adicional.

## Plataformas Suportadas
- **WhatsApp** (API Oficial Meta): requer Phone Number ID, Access Token e Webhook Verify Token. Taxa de uso da API paga pelo cliente diretamente a Meta (~R\$ 0,03-0,12/conversa).
- **Telegram** (gratuito): requer Token do bot (@BotFather) e Username do bot. Zero taxa de API.

## Fluxo de Coleta

### Passo 1 — Plataforma (todos os planos)
Pergunta qual plataforma o cliente escolheu. Determina as credenciais de API a coletar.

**WhatsApp:** meta_phone_number_id → meta_whatsapp_token → meta_webhook_verify_token
**Telegram:** telegram_bot_token → telegram_bot_username

### Passo 2 — Dados da Empresa (todos os planos)
empresa_nome, horario_funcionamento, tom_de_voz, transbordo_nome, transbordo_contato, site_ou_redes, servicos_produtos, faq_perguntas

### Passo 3 — Secretaria Virtual (adicional)
agenda_servicos, agenda_email_google, agenda_politica_cancel, agenda_max_dia, agenda_intervalo_min

### Passo 4 — Ecossistema Completo (adicional ao Passo 3)
crm_atual, equipe_estrutura, redes_integrar, metricas_dashboard, regras_escalacao

## Retornos
- `status: bloqueado` — pagamento nao confirmado
- `status: em_progresso` — inclui `instruction` com proxima pergunta e progresso %
- `status: completo` — inclui `dados` (dict completo), `resumo` e `instruction` de conclusao

## Nota sobre taxa Meta
Quando for coletar credenciais WhatsApp (meta_phone_number_id), a skill injeta automaticamente uma instrucao para Sofia explicar a taxa da API Meta de forma tranquilizadora antes de pedir as chaves.