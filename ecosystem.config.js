
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
