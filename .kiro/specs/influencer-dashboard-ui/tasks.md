# Rencana Implementasi: Influencer Dashboard UI

## Ikhtisar

Implementasi frontend Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui untuk dashboard monitoring influencer TikTok. Semua kode ditempatkan di folder `dashboard/` di root project. Setiap task dibangun secara inkremental dan saling terhubung hingga aplikasi berjalan penuh.

## Tasks

- [x] 1. Inisialisasi project dan konfigurasi dasar
  - Buat folder `dashboard/` dengan struktur Next.js 14 App Router
  - Buat `dashboard/package.json` dengan dependensi: next, react, typescript, tailwindcss, shadcn/ui, recharts, @tanstack/react-query, axios, fast-check, vitest, @testing-library/react
  - Buat `dashboard/tsconfig.json`, `dashboard/tailwind.config.ts`, `dashboard/next.config.ts`
  - Buat `dashboard/src/app/layout.tsx` sebagai root layout dengan dark mode class
  - _Persyaratan: 9.4_

- [x] 2. Definisi types dan API client
  - [x] 2.1 Buat `dashboard/src/types/api.ts` dengan semua TypeScript interfaces
    - Definisikan: `LoginResponse`, `AffiliateCardResponse`, `PaginatedAffiliateResponse`, `AffiliateDetailResponse`, `CampaignResponse`, `CampaignReportResponse`, `GMVDataPoint`, `InfluencerFilters`
    - _Persyaratan: 1.2, 3.2, 4.1, 5.1, 6.1_

  - [x] 2.2 Buat `dashboard/src/lib/api-client.ts` dengan Axios instance dan interceptors
    - Sisipkan `Authorization: Bearer <token>` pada setiap request via request interceptor
    - Tangani response 401 → hapus token + redirect `/login`
    - Tangani response 500 → trigger toast error global
    - Tangani network error → trigger toast error koneksi
    - _Persyaratan: 1.5, 10.1, 10.2, 10.3_

  - [x] 2.3 Tulis property test untuk API client (Property 1)
    - **Property 1: Token disertakan pada setiap request terautentikasi**
    - **Memvalidasi: Persyaratan 1.5**

  - [x] 2.4 Buat `dashboard/src/lib/auth.ts` dengan helper: `getToken()`, `setToken()`, `removeToken()`
    - _Persyaratan: 1.2, 1.4_

  - [x] 2.5 Buat `dashboard/src/lib/formatters.ts` dengan fungsi: `formatFollowerCount()`, `formatEngagementRate()`, `formatCurrency()`, `formatDate()`
    - `formatFollowerCount`: bilangan bulat positif → string singkat (K/M)
    - `formatEngagementRate`: float 0–100 → string dengan tepat dua desimal + `%`
    - `formatCurrency`: angka → format IDR
    - _Persyaratan: 8.5, 8.6_

  - [x] 2.6 Tulis property test untuk formatters (Property 5 dan 11)
    - **Property 5: Format follower count selalu singkat dan valid**
    - **Property 11: Format engagement rate selalu dua angka desimal**
    - **Memvalidasi: Persyaratan 8.5, 8.6**

- [x] 3. Checkpoint — Pastikan semua tests lulus
  - Pastikan semua tests lulus, tanyakan kepada user jika ada pertanyaan.

- [x] 4. Komponen UI dasar
  - [x] 4.1 Buat `dashboard/src/components/ui/` dengan komponen shadcn/ui yang dibutuhkan
    - Tambahkan: Button, Card, Skeleton, Badge, Table, Input, Select, Toast/Sonner
    - _Persyaratan: 2.3, 10.4_

  - [x] 4.2 Buat `dashboard/src/components/MetricCard.tsx`
    - Props: `title`, `value`, `subtitle`, `isLoading`, `icon`
    - Tampilkan Skeleton saat `isLoading === true`
    - _Persyaratan: 2.1, 2.3_

  - [x] 4.3 Tulis property test untuk MetricCard (Property 4)
    - **Property 4: Skeleton loading ditampilkan saat data dimuat**
    - **Memvalidasi: Persyaratan 2.3, 10.4**

  - [x] 4.4 Buat `dashboard/src/components/RankBadge.tsx`
    - Ekspor fungsi `getRankBadgeColor(rank: number): string`
    - Warna: rank 1–3 = emas, rank 4–10 = perak, rank > 10 = abu-abu
    - _Persyaratan: 8.4_

  - [x]* 4.5 Tulis property test untuk RankBadge (Property 7)
    - **Property 7: RankBadge selalu menampilkan warna yang sesuai dengan peringkat**
    - **Memvalidasi: Persyaratan 8.4**

  - [x] 4.6 Buat `dashboard/src/components/StatusIndicator.tsx`
    - Ekspor fungsi `getStatusColor(status: CampaignStatus): string`
    - Warna: ACTIVE=hijau, DRAFT=abu-abu, PAUSED=kuning, STOPPED=merah, COMPLETED=biru
    - _Persyaratan: 5.3_

  - [x]* 4.7 Tulis property test untuk StatusIndicator (Property 8)
    - **Property 8: StatusIndicator selalu menampilkan warna yang sesuai dengan status**
    - **Memvalidasi: Persyaratan 5.3**

- [x] 5. Komponen GMVChart dan InfluencerTable
  - [x] 5.1 Buat `dashboard/src/components/GMVChart.tsx`
    - Gunakan Recharts `LineChart` atau `AreaChart`
    - Props: `data`, `mode`, `onModeChange`, `isLoading`
    - Tampilkan toggle mode: harian / mingguan / bulanan
    - Tooltip dengan nilai GMV (format IDR) dan tanggal
    - Sumbu X: label tanggal sesuai mode; Sumbu Y: format IDR
    - Responsif dengan `ResponsiveContainer`
    - _Persyaratan: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 5.2 Buat `dashboard/src/components/InfluencerTable.tsx`
    - Ekspor fungsi `toggleSortDirection(clickedField, activeField, currentDirection)`
    - Props: `data`, `isLoading`, `onRowClick`, `sortField`, `sortDirection`, `onSort`
    - Header kolom dapat diklik untuk sorting; tampilkan ikon panah pada kolom aktif
    - Kolom: Nama+Foto, Follower Count (format singkat), Engagement Rate (2 desimal), Kategori, Lokasi, GMV Total, Peringkat (RankBadge)
    - _Persyaratan: 3.1, 3.3, 8.1, 8.2, 8.3, 8.5, 8.6_

  - [x] 5.3 Tulis property test untuk InfluencerTable (Property 6)
    - **Property 6: Sorting tabel membalik arah saat kolom yang sama diklik dua kali**
    - **Memvalidasi: Persyaratan 8.2**

- [x] 6. Checkpoint — Pastikan semua tests lulus
  - Pastikan semua tests lulus, tanyakan kepada user jika ada pertanyaan.

- [x] 7. Hooks React Query
  - [x] 7.1 Buat `dashboard/src/hooks/useAuth.ts`
    - Fungsi `login(email, password)` → POST `/api/v1/auth/login` → simpan token
    - Fungsi `logout()` → POST `/api/v1/auth/logout` → hapus token + redirect
    - _Persyaratan: 1.2, 1.4, 9.3_

  - [x] 7.2 Buat `dashboard/src/hooks/useAffiliates.ts`
    - `useAffiliates(filters: InfluencerFilters)` → GET `/api/v1/affiliates/search`
    - `useAffiliateDetail(id: string)` → GET `/api/v1/affiliates/{id}`
    - Ekspor fungsi `buildAffiliateQueryParams(filters)` yang deterministik
    - _Persyaratan: 3.2, 3.5, 4.1_

  - [x] 7.3 Tulis property test untuk buildAffiliateQueryParams (Property 9)
    - **Property 9: Filter influencer selalu menghasilkan query parameter yang konsisten**
    - **Memvalidasi: Persyaratan 3.5**

  - [x] 7.4 Buat `dashboard/src/hooks/useCampaigns.ts`
    - `useCampaigns()` → GET `/api/v1/campaigns`
    - `useCampaignReport(id: string)` → GET `/api/v1/campaigns/{id}/report`
    - _Persyaratan: 5.1, 5.4_

  - [x] 7.5 Buat `dashboard/src/hooks/useReports.ts`
    - `useReports()` → GET `/api/v1/reports/campaigns`
    - Ekspor fungsi `calculateROI(totalGmv, costPerConversion, totalInfluencers): number`
    - _Persyaratan: 6.1, 6.4_

  - [x]* 7.6 Tulis property test untuk calculateROI (Property 10)
    - **Property 10: Kalkulasi ROI menghasilkan nilai yang konsisten**
    - **Memvalidasi: Persyaratan 6.4**

- [x] 8. Middleware dan autentikasi route
  - Buat `dashboard/src/middleware.ts` untuk proteksi route
  - Redirect ke `/login` jika tidak ada token untuk semua route di `/(dashboard)`
  - _Persyaratan: 1.1_

  - [x]* 8.1 Tulis property test untuk middleware redirect (Property 2)
    - **Property 2: Redirect ke login saat tidak terautentikasi**
    - **Memvalidasi: Persyaratan 1.1**

- [x] 9. Halaman Login
  - Buat `dashboard/src/app/(auth)/login/page.tsx`
  - Form dengan field email dan password
  - Panggil `useAuth().login()` saat submit
  - Tampilkan pesan error "Email atau kata sandi tidak valid" saat 401 (tanpa detail teknis)
  - _Persyaratan: 1.2, 1.3_

  - [x] 9.1 Tulis unit test untuk pesan error login (Property 3)
    - **Property 3: Pesan error 401 tidak mengungkap detail teknis**
    - **Memvalidasi: Persyaratan 1.3**

- [x] 10. Layout dashboard dan Sidebar
  - Buat `dashboard/src/components/Sidebar.tsx` dengan navigasi: Dashboard (`/`), Influencer (`/influencers`), Kampanye (`/campaigns`), Laporan (`/reports`)
  - Tampilkan indikator halaman aktif berdasarkan `currentPath`
  - Buat `dashboard/src/app/(dashboard)/layout.tsx` dengan Sidebar + header (nama user + tombol logout)
  - _Persyaratan: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [x] 11. Dashboard utama
  - Buat `dashboard/src/app/(dashboard)/page.tsx`
  - Tampilkan 4 MetricCard: Total GMV, Total Influencer Aktif, Acceptance Rate rata-rata, Total Konversi
  - Data dari `useReports()` → GET `/api/v1/reports/campaigns`
  - Tampilkan skeleton saat loading; tampilkan pesan error + tombol "Coba Lagi" saat gagal
  - Tampilkan top 5 influencer berdasarkan GMV tertinggi
  - Tampilkan daftar kampanye aktif dengan StatusIndicator
  - _Persyaratan: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 12. Halaman Daftar Influencer
  - Buat `dashboard/src/app/(dashboard)/influencers/page.tsx`
  - Gunakan `useAffiliates(filters)` dengan pagination default `page=1&page_size=20`
  - Tampilkan InfluencerTable dengan sorting state lokal
  - Sediakan panel filter: rentang follower, min engagement rate, kategori, lokasi
  - Tampilkan pagination dengan info total data
  - Navigasi ke `/influencers/[id]` saat baris diklik
  - _Persyaratan: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [x] 13. Halaman Detail Influencer
  - Buat `dashboard/src/app/(dashboard)/influencers/[id]/page.tsx`
  - Gunakan `useAffiliateDetail(id)` → GET `/api/v1/affiliates/{id}`
  - Tampilkan: foto profil, nama, bio, lokasi, follower, engagement rate, kategori, tautan TikTok
  - Tampilkan GMVChart dengan data tren GMV dari riwayat kampanye
  - Tampilkan tabel riwayat kampanye beserta GMV per kampanye
  - Tampilkan estimasi komisi dari total GMV
  - Tampilkan halaman "Influencer tidak ditemukan" + tombol kembali saat 404
  - _Persyaratan: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 14. Halaman Kampanye
  - Buat `dashboard/src/app/(dashboard)/campaigns/page.tsx`
  - Gunakan `useCampaigns()` → GET `/api/v1/campaigns`
  - Tampilkan setiap kampanye: nama, deskripsi, tanggal, StatusIndicator, acceptance rate, total GMV
  - Tampilkan metrik ringkasan per kampanye: total influencer, acceptance rate, total views, total GMV
  - Klik kampanye → panggil `useCampaignReport(id)` dan tampilkan detail laporan
  - Tampilkan pesan "Belum ada kampanye" + ilustrasi kosong saat list kosong
  - _Persyaratan: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 15. Halaman Laporan
  - Buat `dashboard/src/app/(dashboard)/reports/page.tsx`
  - Gunakan `useReports()` → GET `/api/v1/reports/campaigns`
  - Tampilkan bar chart perbandingan GMV antar kampanye menggunakan GMVChart
  - Tampilkan tabel ranking influencer: peringkat, nama, GMV total, acceptance rate, total views, cost per conversion
  - Hitung dan tampilkan ROI per kampanye menggunakan `calculateROI()`
  - Sediakan filter rentang tanggal
  - Sediakan tombol ekspor CSV/Excel/PDF → POST `/api/v1/reports/export` → unduh file otomatis
  - _Persyaratan: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [x] 16. Halaman 404 dan penanganan error global
  - Buat `dashboard/src/app/not-found.tsx` dengan pesan dan tombol kembali ke Dashboard
  - Pastikan QueryClientProvider dan Toaster terpasang di root layout
  - _Persyaratan: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 17. Checkpoint akhir — Pastikan semua tests lulus
  - Pastikan semua tests lulus, tanyakan kepada user jika ada pertanyaan.

## Catatan

- Task bertanda `*` bersifat opsional dan dapat dilewati untuk MVP yang lebih cepat
- Setiap task mereferensikan persyaratan spesifik untuk keterlacakan
- Property tests menggunakan library **fast-check** dengan minimum 100 iterasi per properti
- Setiap property test diberi tag komentar: `// Feature: influencer-dashboard-ui, Property {N}: {deskripsi}`
- Unit tests menggunakan **Vitest** + **React Testing Library**
- Jalankan tests dengan: `cd dashboard && npm test`
