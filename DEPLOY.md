# Panduan Deploy

## Persiapan: Push ke GitHub

```bash
# Di terminal, dari root project
git init
git add .
git commit -m "initial commit"

# Buat repo baru di github.com, lalu:
git remote add origin https://github.com/USERNAME/REPO_NAME.git
git push -u origin main
```

---

## 1. Deploy Backend ke Railway

### A. Buat akun Railway
1. Buka https://railway.app
2. Login dengan GitHub

### B. Deploy backend
1. Klik **New Project**
2. Pilih **Deploy from GitHub repo**
3. Pilih repo yang sudah di-push
4. Railway otomatis detect Python dan mulai build

### C. Tambah PostgreSQL
1. Di project Railway, klik **+ New**
2. Pilih **Database** → **Add PostgreSQL**
3. Setelah selesai, klik PostgreSQL → tab **Variables**
4. Copy nilai `DATABASE_URL`

### D. Set Environment Variables di Railway
Klik service backend → tab **Variables** → tambah:

```
DATABASE_URL        = (paste dari PostgreSQL, ganti postgresql:// dengan postgresql+asyncpg://)
JWT_SECRET_KEY      = (buat random string, contoh: openssl rand -hex 32)
REDIS_URL           = redis://localhost:6379/0
ALLOWED_ORIGINS     = https://YOUR_APP.vercel.app
```

### E. Dapatkan URL backend
Setelah deploy sukses, Railway kasih URL seperti:
`https://your-app.up.railway.app`

---

## 2. Deploy Frontend ke Vercel

### A. Buat akun Vercel
1. Buka https://vercel.com
2. Login dengan GitHub

### B. Deploy frontend
1. Klik **New Project**
2. Import repo yang sama
3. **PENTING**: Set **Root Directory** ke `dashboard`
4. Di bagian **Environment Variables**, tambah:
   ```
   NEXT_PUBLIC_API_URL = https://your-app.up.railway.app/api/v1
   ```
5. Klik **Deploy**

### C. Dapatkan URL frontend
Vercel kasih URL seperti: `https://your-app.vercel.app`

---

## 3. Update CORS di Railway

Setelah dapat URL Vercel, update environment variable di Railway:
```
ALLOWED_ORIGINS = https://your-app.vercel.app
```

---

## Update setelah deploy

Setiap kali ada perubahan kode:
```bash
git add .
git commit -m "update: deskripsi perubahan"
git push
```
Railway dan Vercel otomatis rebuild dan deploy ulang.

---

## Troubleshooting

**Backend error "DATABASE_URL invalid"**
- Pastikan URL menggunakan `postgresql+asyncpg://` bukan `postgresql://`

**Frontend "Gagal terhubung ke server"**
- Pastikan `NEXT_PUBLIC_API_URL` sudah diset di Vercel
- Pastikan URL backend Railway sudah benar

**CORS error di browser**
- Update `ALLOWED_ORIGINS` di Railway dengan URL Vercel yang benar
