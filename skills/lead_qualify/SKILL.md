# Skill: Lead Qualify

## Objetivo
Qualificar leads detectando niche, volume e dor principal. Tratar objecoes com scripts empaticos, incluindo a objecao especifica sobre a taxa Meta da API do WhatsApp.

## Deteccoes
- **Niche**: clinica_estetica, clinica_saude, restaurante, ecommerce, imobiliaria, automotivo, educacao, servicos, varejo
- **Volume**: numerico direto ou faixas linguisticas ("poucos", "muitos", "dezenas")
- **Dor**: demora_no_atendimento, perda_de_vendas, agendamento, equipe_reduzida, atendimento_fora_horario
- **Plataforma preferida**: whatsapp/telegram detectado na conversa
- **Objecoes**: preco, tempo, duvida, concorrente, desconfianca, **meta_taxa** (nova)

## Objecao meta_taxa
Detectada por palavras como "taxa meta", "taxa api", "pagar meta", "cobrado por mensagem".
Resposta padrao: explica que ~R$ 0,03-0,12/conversa, pago pelo cliente direto a Meta, e oferece Telegram como alternativa gratuita.

## Retornos
- `ok`: dados completos com plano recomendado + platform_preference
- `objection`: tipo da objecao + suggested_response + instruction
- `missing`: campos faltantes + proxima pergunta
- `error`: mensagem de erro