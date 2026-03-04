module.exports = {
  apps: [
    {
      name: "sofia-bot",
      script: "main.py",
      interpreter: "./.venv/bin/python",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "production",
        PORT: 9000
      }
    },
    {
      name: "sofia-dashboard",
      script: "streamlit",
      args: "run dashboard.py --server.port 9501 --server.address 0.0.0.0",
      interpreter: "./.venv/bin/python",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G"
    }
  ]
};
