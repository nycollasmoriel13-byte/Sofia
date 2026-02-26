Skill: Onboarding — Implementação

Objetivo:
Coletar os dados técnicos necessários para a ativação e configuração final do serviço após confirmação do pagamento.

Quando ativar:
- Somente após pagamento confirmado (status == 'ativo' na tabela `assinaturas`).

Perguntas obrigatórias (sequência recomendada):
1) "Qual o número de WhatsApp que vamos conectar?" (incluir código do país quando possível)
2) "Pode descrever em 3 tópicos o que o bot deve responder obrigatoriamente?" (lista curta de requisitos)
3) "Qual o link do seu site ou redes sociais para eu estudar o tom da sua empresa?"

Formato de saída esperado:
- Resumo em texto que repita os três itens coletados e descreva próximos passos técnicos (ex.: cronograma de integração e necessidade de acesso a APIs ou painel).

Regras e notas:
- Antes de perguntar, verifique o status de assinatura (o hook determinístico será responsável por isso).
- Se algum campo estiver em falta, pedir apenas o campo em falta (perguntas objetivas e curtas).
- Salvar os dados de onboarding no banco local (`onboarding_data` table criada automaticamente se necessário).
- Sempre que coletar uma informação (como o site), confirme com o usuário e diga que está registrando no sistema de ativação.

Tom: Profissional, direto e claro. Use emoji de confirmação quando a coleta estiver completa.

---
