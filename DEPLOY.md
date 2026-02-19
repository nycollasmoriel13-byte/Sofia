# Deploy: Nginx + PM2 setup for Sofia

Follow these commands on your DigitalOcean VPS (replace the IP with your domain if you have one).

1. Install Nginx

```bash
sudo apt update
sudo apt install nginx -y
```

1. Copy the site config to Nginx

On the server create the file `/etc/nginx/sites-available/sofia` and paste the content of `deploy/nginx/sofia` from this repo (or upload it).

1. Enable the site and restart Nginx

```bash
sudo ln -s /etc/nginx/sites-available/sofia /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

1. (Optional) Enable HTTPS with Certbot (requires domain)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

1. Git + project setup (on the server)

```bash
# clone repo
git clone <REPO_URL> repo && cd repo

# create python venv and install deps
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# install Node + PM2 (if not installed)
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs
npm install -g pm2

# start apps via PM2 using the provided ecosystem file
pm2 start ecosystem.config.js
pm2 save
pm2 status
```

1. Access the services:

- API/Bot/Webhook: `http://67.205.183.59/`
- Dashboard: `http://67.205.183.59/dashboard`

1. To push local changes to GitHub

```bash
git add .
git commit -m "Update: Nginx config and PM2 ecosystem for deployment"
git push origin main
```
