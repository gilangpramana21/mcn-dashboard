# Panduan Deploy ke Hostinger VPS

## Arsitektur
```
Internet → Nginx (port 80) → Next.js (port 3000)
                           → FastAPI (port 8000, via proxy)
PostgreSQL (port 5432, internal)
```

---

## 1. Beli VPS di Hostinger

1. Login ke https://hpanel.hostinger.com
2. Beli **VPS KVM 1** (pilih region Singapore)
3. Pilih OS: **Ubuntu 22.04**
4. Setelah aktif, catat **IP address** dan **password root**

---

## 2. Koneksi ke VPS

```bash
ssh root@IP_VPS_KAMU
```

---

## 3. Jalankan Script Setup Otomatis

```bash
# Di dalam VPS
apt update && apt install -y git
git clone https://github.com/gilangpramana21/mcn-dashboard.git /var/www/mcn-dashboard
cd /var/www/mcn-dashboard
bash deploy/setup.sh
```

Script ini otomatis:
- Install Python, Node.js, PostgreSQL, Nginx, PM2
- Setup database
- Clone & build aplikasi
- Setup systemd service untuk backend
- Setup PM2 untuk frontend
- Konfigurasi Nginx

---

## 4. Set Password Database

Setelah setup selesai, edit file `.env`:

```bash
nano /var/www/mcn-dashboard/.env
```

Ganti `GANTI_PASSWORD_INI` dengan password yang kuat, lalu:

```bash
# Update password di PostgreSQL juga
sudo -u postgres psql -c "ALTER USER mcn_user WITH PASSWORD 'password_baru_kamu';"

# Restart backend
systemctl restart mcn-backend
```

---

## 5. Cek Status

```bash
# Cek backend
systemctl status mcn-backend

# Cek frontend
pm2 status

# Cek Nginx
systemctl status nginx

# Test health check
curl http://localhost:8000/health
```

---

## 6. Akses Dashboard

Buka browser: `http://IP_VPS_KAMU`

---

## Update Kode Setelah Deploy

Setiap ada perubahan kode, push ke GitHub lalu di VPS:

```bash
bash /var/www/mcn-dashboard/deploy/update.sh
```

---

## Troubleshooting

**Backend tidak jalan:**
```bash
journalctl -u mcn-backend -n 50
```

**Frontend tidak jalan:**
```bash
pm2 logs mcn-frontend
```

**Nginx error:**
```bash
nginx -t
cat /var/log/nginx/error.log
```

**Database error:**
```bash
sudo -u postgres psql -d mcn_dashboard -c "\dt"
```
