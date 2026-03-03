"""
Script de teste do Bot Factory
Insere um cliente de teste e monitora a criação automática do bot
"""
import sqlite3
import time
from datetime import datetime

DB_PATH = "agencia_autovenda.db"

def inserir_cliente_teste():
    """Insere um cliente de teste no banco"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Dados do cliente de teste
    user_id = "teste_factory_001"
    nome = "Clínica Estética Bella"
    plano = "flash"
    status = "ativo"
    whatsapp_id = "5511999887766"
    
    # Remove se já existir
    cursor.execute("DELETE FROM assinaturas WHERE user_id = ?", (user_id,))
    
    # Insere na tabela assinaturas (SEM coluna nicho - será inferido)
    cursor.execute("""
        INSERT INTO assinaturas 
        (user_id, nome, plano, status, whatsapp_id, valor_mensal, data_inicio)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, nome, plano, status, whatsapp_id, 49.90, datetime.now().isoformat()))
    
    # Insere dados de onboarding (o nicho será detectado pelos objetivos_ia)
    cursor.execute("DELETE FROM onboarding_data WHERE user_id = ?", (user_id,))
    cursor.execute("""
        INSERT INTO onboarding_data
        (user_id, whatsapp_contato, website_cliente, objetivos_ia, status_configuracao, data_coleta)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        whatsapp_id,
        "www.clinicabella.com.br",
        "Automatizar agendamentos de procedimentos estéticos como botox, preenchimento e limpeza de pele. Responder dúvidas sobre tratamentos.",
        "completo",
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Cliente de teste inserido:")
    print(f"   User ID: {user_id}")
    print(f"   Nome: {nome}")
    print(f"   Plano: {plano}")
    print(f"   Nicho: será detectado automaticamente como 'clinica_estetica'")
    print(f"   Status: {status}")
    print()
    print("🔍 Aguarde até 60 segundos para o Factory detectar e criar o bot...")
    print("💬 Você receberá uma notificação no Telegram quando o bot for criado!")

def verificar_bot_criado():
    """Verifica se o bot foi criado"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT user_id, status, plano, nicho, data_deploy
        FROM bots_gerados 
        WHERE user_id = 'teste_factory_001'
    """)
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        print("\n🎉 BOT CRIADO COM SUCESSO!")
        print(f"   User ID: {result[0]}")
        print(f"   Status: {result[1]}")
        print(f"   Plano: {result[2]}")
        print(f"   Nicho: {result[3]}")
        print(f"   Deploy em: {result[4]}")
        return True
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("🏭 BOT FACTORY - TESTE AUTOMATIZADO")
    print("=" * 60)
    print()
    
    inserir_cliente_teste()
    
    print("\n⏱️  Monitorando criação do bot (máximo 2 minutos)...")
    print("   Pressione Ctrl+C para cancelar\n")
    
    for i in range(24):  # 24 x 5s = 2 minutos
        time.sleep(5)
        if verificar_bot_criado():
            break
        print(f"   [{i*5}s] Verificando... ", end="\r")
    else:
        print("\n⚠️  Tempo limite excedido. Verifique:")
        print("   1. O watcher está rodando? (python bot_factory/watcher.py)")
        print("   2. Consulte o dashboard na aba 🏭 Factory")
        print("   3. Verifique os logs do watcher")
