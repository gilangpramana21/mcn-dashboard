# Panduan Deploy

## Persiapan: Push ke GitHub

```bash
git add .
git commit -m "update: siap deploy"
git push
```

---

## 1. Deploy Backend ke Koyeb (Gratis, tanpa kartu kredit)

### A. Buat akun Koyeb
1. Buka https://app.koyeb.com
2. Klik **Sign up with GitHub** — tidak perlu kartu kredit

### B. Buat App baru
1. Klik **Create App**
2. Pilih **GitHub** sebagai sumber
3. Pilih repo `mcn-dashboard`, branch `main`
4. **Root directory**: kosongkan (biarkan default `/`)

### C. Konfigurasi Build & Run
- **Build command**: `pip install -r requirements.txt`
- **Run command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Port**: `8000`

### D. Tambah Database PostgreSQL di Koyeb
1. Di dashboard Koyeb, klik **Databases** di sidebar
2. Klik **Create Database** → pilih **PostgreSQL**
3. Pilih region terdekat (Singapore)
4. Setelah selesai, copy **Connection string** (format: `postgresql://...`)

### E. Set Environment Variables
Di halaman App → tab **Environment**, tambah:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/dbname` (dari Koyeb DB, ganti `postgresql://` → `postgresql+asyncpg://`) |
| `JWT_SECRET_KEY` | buat random string panjang (contoh: `openssl rand -hex 32`) |
| `REDIS_URL` | `redis://localhost:6379/0` (atau kosongkan, app akan pakai memory cache) |
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app` (isi setelah dapat URL Vercel) |

### F. Deploy
Klik **Deploy** — Koyeb akan build dan deploy otomatis.

Setelah selesai, Koyeb kasih URL seperti:
`https://mcn-backend-xxx.koyeb.app`

### G. Jalankan Migrasi Database
Setelah backend live, jalankan migrasi via endpoint atau manual:
```bash
# Test health check dulu
curl https://mcn-backend-xxx.koyeb.app/health
```

---

## 2. Deploy Frontend ke Vercel (Gratis)

### A. Buat akun Vercel
1. Buka https://vercel.com
2. Login dengan GitHub

### B. Import Project
1. Klik **Add New Project**
2. Import repo `mcn-dashboard`
3. **PENTING**: Set **Root Directory** ke `dashboard`
4. Framework akan terdeteksi otomatis sebagai **Next.js**

### C. Set Environment Variables
Di bagian **Environment Variables**, tambah:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://mcn-backend-xxx.koyeb.app/api/v1` |

5. Klik **Deploy**

Vercel kasih URL seperti: `https://mcn-dashboard-xxx.vercel.app`

---

## 3. Update CORS Backend

Setelah dapat URL Vercel, update env var di Koyeb:
```
ALLOWED_ORIGINS = https://mcn-dashboard-xxx.vercel.app
```

---

## Update Kode Setelah Deploy

Setiap kali ada perubahan:
```bash
git add .
git commit -m "update: deskripsi perubahan"
git push
```
Koyeb dan Vercel otomatis rebuild dan deploy ulang.

---

## Troubleshooting

**Backend error "DATABASE_URL invalid"**
- Pastikan URL menggunakan `postgresql+asyncpg://` bukan `postgresql://`

**Frontend "Gagal terhubung ke server"**
- Pastikan `NEXT_PUBLIC_API_URL` sudah diset di Vercel
- Pastikan URL backend Koyeb sudah benar (cek `/health`)

**CORS error di browser**
- Update `ALLOWED_ORIGINS` di Koyeb dengan URL Vercel yang benar

**Build gagal di Koyeb**
- Pastikan `requirements.txt` ada di root project
- Cek log build di Koyeb dashboard

**Redis tidak tersedia**
- App akan otomatis fallback ke memory cache, tidak masalah untuk production kecil
