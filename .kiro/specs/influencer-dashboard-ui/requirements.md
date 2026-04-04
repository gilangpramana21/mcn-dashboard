# Dokumen Persyaratan

## Pendahuluan

Dashboard UI untuk Sistem Agen Cerdas Pemasaran Influencer TikTok adalah antarmuka frontend berbasis web yang dibangun dengan React + Next.js 14 (App Router) dan TypeScript. Dashboard ini mengonsumsi REST API FastAPI yang sudah ada (berjalan di port 8000) untuk menampilkan data performa dan revenue influencer/affiliator, metrik kampanye, serta laporan GMV secara visual dan interaktif.

Tampilan mengikuti desain dark mode modern bergaya Vercel/Linear — minimalis, padat informasi, dan responsif.

## Glosarium

- **Dashboard**: Antarmuka web utama yang menampilkan ringkasan metrik dan navigasi ke halaman lain
- **Influencer**: Kreator konten TikTok yang terdaftar sebagai affiliate dalam sistem
- **Affiliator**: Sebutan lain untuk Influencer dalam konteks program afiliasi
- **GMV** (Gross Merchandise Value): Total nilai transaksi yang dihasilkan dari konten influencer
- **Kampanye**: Program pemasaran yang melibatkan sejumlah influencer dalam periode tertentu
- **Acceptance Rate**: Persentase influencer yang menerima undangan kampanye
- **Engagement Rate**: Rasio interaksi (like, komentar, share) terhadap jumlah penonton konten
- **ROI** (Return on Investment): Rasio keuntungan terhadap biaya kampanye
- **Komisi**: Estimasi pendapatan influencer berdasarkan persentase GMV yang dihasilkan
- **API_Client**: Modul frontend yang bertanggung jawab mengonsumsi REST API backend
- **Auth_Module**: Modul frontend yang mengelola autentikasi dan sesi pengguna
- **Dashboard_Page**: Halaman utama dashboard yang menampilkan ringkasan metrik
- **Influencer_List_Page**: Halaman daftar semua influencer/affiliator
- **Influencer_Detail_Page**: Halaman profil lengkap satu influencer
- **Campaign_Page**: Halaman daftar dan manajemen kampanye
- **Report_Page**: Halaman laporan perbandingan GMV dan ROI
- **Metric_Card**: Komponen kartu yang menampilkan satu metrik utama
- **GMV_Chart**: Komponen grafik tren GMV berbasis Recharts
- **Influencer_Table**: Komponen tabel influencer dengan sorting dan filtering
- **Rank_Badge**: Komponen badge peringkat influencer berdasarkan GMV
- **Status_Indicator**: Komponen indikator status kampanye

---

## Persyaratan

### Persyaratan 1: Autentikasi Pengguna

**User Story:** Sebagai pengguna sistem, saya ingin login dengan kredensial yang valid, agar saya dapat mengakses dashboard secara aman.

#### Kriteria Penerimaan

1. WHEN pengguna mengakses halaman yang memerlukan autentikasi tanpa sesi aktif, THE Auth_Module SHALL mengarahkan pengguna ke halaman login
2. WHEN pengguna mengirimkan kredensial yang valid ke endpoint `POST /api/v1/auth/login`, THE Auth_Module SHALL menyimpan JWT token di `httpOnly cookie` atau `localStorage` dan mengarahkan pengguna ke Dashboard_Page
3. IF endpoint `POST /api/v1/auth/login` mengembalikan status 401, THEN THE Auth_Module SHALL menampilkan pesan kesalahan "Email atau kata sandi tidak valid" tanpa mengungkap detail teknis
4. WHEN sesi pengguna berakhir atau token kedaluwarsa, THE Auth_Module SHALL menghapus token yang tersimpan dan mengarahkan pengguna ke halaman login
5. THE Auth_Module SHALL menyertakan JWT token pada setiap permintaan HTTP ke backend sebagai `Authorization: Bearer <token>`

---

### Persyaratan 2: Dashboard Utama — Ringkasan Metrik

**User Story:** Sebagai manajer kampanye, saya ingin melihat ringkasan metrik utama di satu halaman, agar saya dapat memantau performa keseluruhan program afiliasi dengan cepat.

#### Kriteria Penerimaan

1. THE Dashboard_Page SHALL menampilkan empat Metric_Card: Total GMV, Total Influencer Aktif, Acceptance Rate rata-rata, dan Total Konversi (total_views)
2. WHEN Dashboard_Page dimuat, THE API_Client SHALL mengambil data dari `GET /api/v1/reports/campaigns` untuk mengisi Metric_Card
3. WHEN data sedang dimuat dari API, THE Dashboard_Page SHALL menampilkan skeleton loading pada setiap Metric_Card
4. IF `GET /api/v1/reports/campaigns` mengembalikan error, THEN THE Dashboard_Page SHALL menampilkan pesan kesalahan dan tombol "Coba Lagi"
5. THE Dashboard_Page SHALL menampilkan daftar top 5 influencer berdasarkan GMV tertinggi dari data affiliates
6. THE Dashboard_Page SHALL menampilkan daftar kampanye aktif beserta Status_Indicator masing-masing

---

### Persyaratan 3: Daftar Influencer/Affiliator

**User Story:** Sebagai manajer kampanye, saya ingin melihat semua influencer dalam tabel yang dapat diurutkan dan difilter, agar saya dapat menemukan influencer yang sesuai dengan kebutuhan kampanye.

#### Kriteria Penerimaan

1. THE Influencer_List_Page SHALL menampilkan Influencer_Table dengan kolom: Nama, Foto, Follower Count, Engagement Rate, Kategori Konten, Lokasi, GMV Total, dan Peringkat
2. WHEN Influencer_List_Page dimuat, THE API_Client SHALL mengambil data dari `GET /api/v1/affiliates/search` dengan pagination default `page=1&page_size=20`
3. THE Influencer_Table SHALL mendukung sorting ascending/descending pada kolom: Follower Count, Engagement Rate, dan GMV Total
4. THE Influencer_List_Page SHALL menyediakan filter berdasarkan: rentang follower (min/max), minimum engagement rate, kategori konten, dan lokasi
5. WHEN pengguna mengubah parameter filter, THE API_Client SHALL mengirim ulang permintaan ke `GET /api/v1/affiliates/search` dengan parameter filter yang diperbarui
6. THE Influencer_List_Page SHALL menampilkan pagination dengan informasi total data dan navigasi halaman
7. THE Influencer_Table SHALL menampilkan Rank_Badge pada setiap baris berdasarkan peringkat GMV influencer tersebut
8. WHEN pengguna mengklik baris influencer, THE Influencer_List_Page SHALL mengarahkan pengguna ke Influencer_Detail_Page yang sesuai

---

### Persyaratan 4: Detail Influencer

**User Story:** Sebagai manajer kampanye, saya ingin melihat profil lengkap seorang influencer beserta statistik performanya, agar saya dapat membuat keputusan yang tepat tentang keterlibatan influencer tersebut.

#### Kriteria Penerimaan

1. WHEN Influencer_Detail_Page dimuat dengan `affiliate_id` tertentu, THE API_Client SHALL mengambil data dari `GET /api/v1/affiliates/{id}`
2. THE Influencer_Detail_Page SHALL menampilkan: foto profil, nama, bio, lokasi, jumlah follower, engagement rate, kategori konten, dan tautan profil TikTok
3. THE Influencer_Detail_Page SHALL menampilkan GMV_Chart yang memvisualisasikan tren GMV influencer tersebut dari riwayat kampanye
4. THE Influencer_Detail_Page SHALL menampilkan tabel riwayat kampanye yang pernah diikuti influencer beserta GMV per kampanye
5. THE Influencer_Detail_Page SHALL menampilkan estimasi komisi berdasarkan persentase standar dari total GMV
6. IF `GET /api/v1/affiliates/{id}` mengembalikan status 404, THEN THE Influencer_Detail_Page SHALL menampilkan halaman "Influencer tidak ditemukan" dengan tombol kembali ke daftar
7. WHERE influencer memiliki `tiktok_profile_url`, THE Influencer_Detail_Page SHALL menampilkan tautan yang dapat diklik menuju profil TikTok

---

### Persyaratan 5: Halaman Kampanye

**User Story:** Sebagai manajer kampanye, saya ingin melihat semua kampanye beserta statusnya, agar saya dapat memantau progress dan performa setiap kampanye.

#### Kriteria Penerimaan

1. WHEN Campaign_Page dimuat, THE API_Client SHALL mengambil data dari `GET /api/v1/campaigns` untuk menampilkan daftar kampanye
2. THE Campaign_Page SHALL menampilkan setiap kampanye dengan informasi: nama, deskripsi, tanggal mulai, tanggal selesai, Status_Indicator, acceptance rate, dan total GMV
3. THE Status_Indicator SHALL menampilkan warna berbeda untuk setiap status kampanye: hijau untuk `active`, abu-abu untuk `draft`, kuning untuk `paused`, merah untuk `stopped`, dan biru untuk `completed`
4. WHEN pengguna mengklik kampanye, THE API_Client SHALL mengambil data dari `GET /api/v1/campaigns/{id}/report` dan menampilkan detail laporan kampanye tersebut
5. THE Campaign_Page SHALL menampilkan metrik ringkasan per kampanye: total influencer, acceptance rate, total views, dan total GMV
6. IF `GET /api/v1/campaigns` mengembalikan daftar kosong, THEN THE Campaign_Page SHALL menampilkan pesan "Belum ada kampanye" dengan ilustrasi kosong

---

### Persyaratan 6: Halaman Laporan — Perbandingan GMV dan ROI

**User Story:** Sebagai manajer kampanye, saya ingin melihat laporan perbandingan GMV antar influencer dan ROI per kampanye dalam bentuk grafik, agar saya dapat menganalisis efektivitas program afiliasi secara menyeluruh.

#### Kriteria Penerimaan

1. WHEN Report_Page dimuat, THE API_Client SHALL mengambil data dari `GET /api/v1/reports/campaigns` untuk mengisi semua grafik dan tabel laporan
2. THE Report_Page SHALL menampilkan bar chart perbandingan GMV antar kampanye menggunakan komponen GMV_Chart
3. THE Report_Page SHALL menampilkan tabel ranking influencer berdasarkan GMV dengan kolom: peringkat, nama, GMV total, acceptance rate, total views, dan cost per conversion
4. THE Report_Page SHALL menghitung dan menampilkan ROI per kampanye dengan formula: `ROI = (total_gmv - cost_per_conversion * total_influencers) / (cost_per_conversion * total_influencers) * 100`
5. THE Report_Page SHALL menyediakan tombol ekspor laporan dalam format CSV, Excel, dan PDF yang memanggil `POST /api/v1/reports/export`
6. WHEN pengguna mengklik tombol ekspor, THE API_Client SHALL mengirim permintaan ke `POST /api/v1/reports/export` dan mengunduh file hasil ekspor secara otomatis
7. THE Report_Page SHALL mendukung filter rentang tanggal untuk menyaring data laporan yang ditampilkan

---

### Persyaratan 7: Komponen GMV Chart

**User Story:** Sebagai pengguna dashboard, saya ingin melihat tren GMV dalam bentuk grafik yang interaktif, agar saya dapat memahami pola performa dari waktu ke waktu.

#### Kriteria Penerimaan

1. THE GMV_Chart SHALL diimplementasikan menggunakan library Recharts
2. THE GMV_Chart SHALL mendukung tiga mode tampilan: harian, mingguan, dan bulanan yang dapat dipilih pengguna
3. WHEN pengguna mengarahkan kursor ke titik data pada grafik, THE GMV_Chart SHALL menampilkan tooltip dengan nilai GMV dan tanggal yang tepat
4. THE GMV_Chart SHALL menampilkan sumbu X dengan label tanggal yang diformat sesuai mode tampilan yang dipilih
5. THE GMV_Chart SHALL menampilkan sumbu Y dengan nilai GMV yang diformat dalam satuan mata uang Rupiah (IDR)
6. THE GMV_Chart SHALL responsif terhadap ukuran kontainer dan menyesuaikan tampilan pada layar mobile

---

### Persyaratan 8: Komponen Tabel Influencer

**User Story:** Sebagai pengguna dashboard, saya ingin berinteraksi dengan tabel influencer yang responsif dan mudah digunakan, agar saya dapat menemukan dan membandingkan influencer dengan efisien.

#### Kriteria Penerimaan

1. THE Influencer_Table SHALL menampilkan data dalam format tabel dengan header kolom yang dapat diklik untuk sorting
2. WHEN pengguna mengklik header kolom yang sama dua kali, THE Influencer_Table SHALL membalik urutan sorting dari ascending ke descending atau sebaliknya
3. THE Influencer_Table SHALL menampilkan indikator visual (ikon panah) pada kolom yang sedang aktif diurutkan
4. THE Influencer_Table SHALL menampilkan Rank_Badge dengan warna berbeda: emas untuk peringkat 1-3, perak untuk peringkat 4-10, dan abu-abu untuk peringkat di atas 10
5. THE Influencer_Table SHALL menampilkan engagement rate dalam format persentase dengan dua angka desimal
6. THE Influencer_Table SHALL menampilkan follower count dalam format singkat (contoh: 1.2M, 500K)

---

### Persyaratan 9: Navigasi dan Layout

**User Story:** Sebagai pengguna dashboard, saya ingin navigasi yang konsisten dan intuitif di seluruh halaman, agar saya dapat berpindah antar halaman dengan mudah.

#### Kriteria Penerimaan

1. THE Dashboard SHALL menampilkan sidebar navigasi yang persisten dengan tautan ke: Dashboard, Influencer, Kampanye, dan Laporan
2. THE Dashboard SHALL menampilkan header dengan nama pengguna yang sedang login dan tombol logout
3. WHEN pengguna mengklik tombol logout, THE Auth_Module SHALL menghapus token sesi dan mengarahkan ke halaman login
4. THE Dashboard SHALL menerapkan tema dark mode secara konsisten di seluruh halaman menggunakan palet warna yang seragam
5. THE Dashboard SHALL responsif dan dapat digunakan pada layar dengan lebar minimum 768px (tablet) hingga desktop
6. THE Dashboard SHALL menampilkan indikator halaman aktif pada sidebar navigasi sesuai halaman yang sedang dibuka

---

### Persyaratan 10: Penanganan Error dan State Kosong

**User Story:** Sebagai pengguna dashboard, saya ingin mendapatkan umpan balik yang jelas ketika terjadi kesalahan atau data tidak tersedia, agar saya tidak bingung dengan kondisi sistem.

#### Kriteria Penerimaan

1. IF permintaan API gagal karena kesalahan jaringan, THEN THE API_Client SHALL menampilkan notifikasi toast dengan pesan kesalahan yang dapat dipahami pengguna
2. IF permintaan API mengembalikan status 401, THEN THE API_Client SHALL menghapus sesi dan mengarahkan pengguna ke halaman login
3. IF permintaan API mengembalikan status 500, THEN THE API_Client SHALL menampilkan pesan "Terjadi kesalahan pada server. Silakan coba lagi nanti."
4. WHEN data sedang dimuat, THE Dashboard SHALL menampilkan skeleton loading yang sesuai dengan layout konten yang akan ditampilkan
5. IF halaman yang diakses tidak ditemukan, THEN THE Dashboard SHALL menampilkan halaman 404 dengan tombol kembali ke Dashboard_Page
