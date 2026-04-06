#!/bin/bash
# Script update deployment setelah ada perubahan kode
# Jalankan: bash /var/www/mcn-dashboard/deploy/update.sh

set -e

cd /var/www/mcn-dashboard

echo "=== Pull kode terbaru ==="
git pull

echo "=== Update backend dependencies ==="
source venv/bin/activate
pip install -r requirements.txt

echo "=== Restart backend ==="
systemctl restart mcn-backend

echo "=== Build frontend ==="
cd dashboard
npm install
npm run build

echo "=== Restart frontend ==="
pm2 restart mcn-frontend

echo "=== Selesai! ==="
systemctl status mcn-backend --no-pager
pm2 status
