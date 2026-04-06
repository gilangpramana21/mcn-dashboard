#!/bin/bash
# Script setup VPS Hostinger untuk MCN Dashboard
# Jalankan sebagai root: bash setup.sh

set -e

echo "=== MCN Dashboard VPS Setup ==="

# 1. Update sistem
apt update && apt upgrade -y

# 2. Install dependencies
apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib nginx git curl

# 3. Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# 4. Install PM2
npm install -g pm2

# 5. Setup PostgreSQL
echo "=== Setup PostgreSQL ==="
sudo -u postgres psql -c "CREATE DATABASE mcn_dashboard;" 2>/dev/null || echo "Database sudah ada"
sudo -u postgres psql -c "CREATE USER mcn_user WITH PASSWORD 'GANTI_PASSWORD_INI';" 2>/dev/null || echo "User sudah ada"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mcn_dashboard TO mcn_user;"
sudo -u postgres psql -c "ALTER DATABASE mcn_dashboard OWNER TO mcn_user;"

# 6. Clone repo
echo "=== Clone Repository ==="
mkdir -p /var/www
cd /var/www
if [ -d "mcn-dashboard" ]; then
    cd mcn-dashboard && git pull
else
    git clone https://github.com/gilangpramana21/mcn-dashboard.git
    cd mcn-dashboard
fi

# 7. Setup Python venv & install backend
echo "=== Setup Backend ==="
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 8. Buat file .env
if [ ! -f ".env" ]; then
    echo "=== Buat file .env ==="
    JWT_SECRET=$(openssl rand -hex 32)
    cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://mcn_user:GANTI_PASSWORD_INI@localhost:5432/mcn_dashboard
JWT_SECRET_KEY=${JWT_SECRET}
REDIS_URL=redis://localhost:6379/0
EOF
    echo "File .env dibuat. JWT_SECRET_KEY: ${JWT_SECRET}"
fi

# 9. Jalankan migrasi database
echo "=== Jalankan Migrasi ==="
source venv/bin/activate
for f in app/db/migrations/*.sql; do
    echo "Menjalankan: $f"
    sudo -u postgres psql -d mcn_dashboard -f "$f" 2>/dev/null || true
done

# 10. Setup systemd service untuk backend
echo "=== Setup Backend Service ==="
cp deploy/mcn-backend.service /etc/systemd/system/
sed -i 's/User=ubuntu/User=root/' /etc/systemd/system/mcn-backend.service
systemctl daemon-reload
systemctl enable mcn-backend
systemctl start mcn-backend

# 11. Build frontend
echo "=== Build Frontend ==="
cd /var/www/mcn-dashboard/dashboard
npm install
npm run build

# 12. Setup PM2 untuk frontend
cp /var/www/mcn-dashboard/deploy/ecosystem.config.js /var/www/mcn-dashboard/dashboard/
pm2 start /var/www/mcn-dashboard/dashboard/ecosystem.config.js
pm2 save
pm2 startup systemd -u root --hp /root | tail -1 | bash

# 13. Setup Nginx
echo "=== Setup Nginx ==="
cp /var/www/mcn-dashboard/deploy/nginx.conf /etc/nginx/sites-available/mcn
ln -sf /etc/nginx/sites-available/mcn /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo "=== SELESAI ==="
echo "Dashboard bisa diakses di: http://$(curl -s ifconfig.me)"
echo ""
echo "PENTING: Edit /var/www/mcn-dashboard/.env dan ganti GANTI_PASSWORD_INI"
echo "Lalu restart backend: systemctl restart mcn-backend"
