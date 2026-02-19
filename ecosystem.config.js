module.exports = {
  apps : [{
    name: 'sofia-bot',
    script: 'app.py',
    interpreter: '/root/sofia/.venv/bin/python',
    cwd: '/root/sofia',
    env: {
      NODE_ENV: 'production',
    },
    // Espera 5 segundos antes de reiniciar se falhar (evita loop infinito)
    restart_delay: 5000,
    // Não reinicia se o uso de memória for muito alto (evita travar o servidor)
    max_memory_restart: '800M',
    // Mescla os logs para facilitar a leitura
    combine_logs: true,
    error_file: '/root/sofia/logs/err.log',
    out_file: '/root/sofia/logs/out.log',
  }]
};

module.exports = {
  apps: [
    {
      name: "sofia-bot",
      script: "main.py",
      // O caminho para o interpretador do ambiente virtual no servidor
      interpreter: "./.venv/bin/python",
      // Reinicia automaticamente se o processo falhar
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "production",
        PORT: 8000
      }
    },
    {
      name: "sofia-dashboard",
      script: "streamlit",
      // Argumentos necessários para o Streamlit rodar corretamente na nuvem
      args: "run dashboard.py --server.port 8501 --server.address 0.0.0.0",
      interpreter: "./.venv/bin/python",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G"
    }
  ]
};
