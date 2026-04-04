# Panduan Deploy

## Persiapan: Push ke GitHub

```bash
git add .
git commit -m "update: siap deploy"
git push
```

---

## 1. Deploy Backend ke Fly.io (Gratis, tanpa kartu kredit)

### A. Install flyctl (CLI Fly.io)

```bash
# macOS
brew install flyctl

# Atau via script
curl -L https://fly.io/install.sh | sh
```

### B. Login ke Fly.io

```bash
flyctl auth signup   # buat akun baru (login via GitHub, tidak perlu kartu kredit)
# atau
flyctl auth login    # kalau sudah punya akun
```

### C. Buat app di Fly.io

```bash
# Di root project (bukan folder dashboard/)
flyctl apps create mcn-backend
```

Kalau nama `mcn-backend` sudah dipakai, ganti dengan nama lain misal `mcn-backend-gilang`.

### D. Buat database PostgreSQL gratis di Fly.io

```bash
flyctl postgres create --name mcn-db --region sin --initial-cluster-size 1 --vm-size shared-cpu-1x --volume-size 1
```

Setelah selesai, attach ke app:

```bash
flyctl postgres attach mcn-db --app mcn-backend
```

Ini otomatis set env var `DATABASE_URL` di app kamu.

### E. Set environment variables

```bash
# JWT secret (generate dulu)
flyctl secrets set JWT_SECRET_KEY="$(openssl rand -hex 32)" --app mcn-backend

# CORS (isi setelah dapat URL Vercel, untuk sekarang bisa wildcard dulu)
flyctl secrets set ALLOWED_ORIGINS="*" --app mcn-backend
```

### F. Deploy

```bash
flyctl deploy --app mcn-backend
```

Tunggu sampai selesai. Fly.io akan build Docker image dan deploy otomatis.

### G. Cek status

```bash
flyctl status --app mcn-backend
```

### H. Test health check

```bash
curl https://mcn-backend.fly.dev/health
# Harus balas: {"status":"ok","version":"1.0.0"}
```

URL backend kamu: `https://mcn-backend.fly.dev`

---

## 2. Deploy Frontend ke Vercel (Gratis)

### A. Buat akun Vercel
1. Buka https://vercel.com
2. Login dengan GitHub

### B. Import Project
1. Klik **Add New Project**
2. Import repo `mcn-dashboard`
3. **PENTING**: Set **Root Directory** ke `dashboard`
4. Framework terdeteksi otomatis sebagai **Next.js**

### C. Set Environment Variables

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://mcn-backend.fly.dev/api/v1` |

5. Klik **Deploy**

URL frontend: `https://mcn-dashboard-xxx.vercel.app`

---

## 3. Update CORS setelah dapat URL Vercel

```bash
flyctl secrets set ALLOWED_ORIGINS="https://mcn-dashboard-xxx.vercel.app" --app mcn-backend
```

---

## Update Kode Setelah Deploy

```bash
git add .
git commit -m "update: deskripsi perubahan"
git push

# Redeploy backend
flyctl deploy --app mcn-backend
```

Vercel otomatis rebuild saat ada push ke GitHub.

---

## Troubleshooting

**`flyctl: command not found`**
- Jalankan ulang terminal setelah install, atau tambah ke PATH:
  `export PATH="$HOME/.fly/bin:$PATH"`

**Backend error "DATABASE_URL invalid"**
- Fly.io otomatis set `DATABASE_URL` dengan format `postgres://...`
- App sudah handle konversi ke `postgresql+asyncpg://` — cek `app/database.py`

**Build gagal**
- Cek log: `flyctl logs --app mcn-backend`

**Frontend "Gagal terhubung ke server"**
- Pastikan `NEXT_PUBLIC_API_URL` sudah diset di Vercel
- Cek CORS: `flyctl secrets list --app mcn-backend`
