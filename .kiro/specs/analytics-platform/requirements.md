# Dokumen Requirements

## Pendahuluan

Platform Analytics adalah ekstensi komprehensif dari Sistem Agen Cerdas Pemasaran Influencer TikTok yang menyediakan kemampuan analitik mendalam untuk mengukur, memantau, dan mengoptimalkan performa kampanye pemasaran influencer. Platform ini mengintegrasikan data dari berbagai sumber (konten video, produk, kreator, dan transaksi) untuk menghasilkan wawasan bisnis yang dapat ditindaklanjuti.

Platform ini dirancang untuk membantu tim pemasaran memahami ROI kampanye, mengidentifikasi kreator dan produk berkinerja tinggi, menganalisis tren konten, dan membuat keputusan berbasis data untuk mengoptimalkan strategi pemasaran influencer.

## Glosarium

- **Platform_Analytics**: Sistem analitik komprehensif yang menyediakan wawasan performa kampanye pemasaran influencer
- **Kreator**: Influencer TikTok yang membuat konten video untuk mempromosikan produk
- **Konten_Video**: Video TikTok yang dibuat oleh kreator untuk mempromosikan produk dalam kampanye
- **Produk**: Item yang dipromosikan melalui kampanye pemasaran influencer
- **GMV**: Gross Merchandise Value, total nilai transaksi yang dihasilkan dari konten video
- **Conversion_Rate**: Persentase viewers yang melakukan pembelian setelah menonton konten
- **Engagement_Rate**: Persentase interaksi (likes, comments, shares) terhadap total views
- **Creator_Score**: Skor komposit yang menilai performa keseluruhan kreator berdasarkan GMV, engagement, dan konsistensi
- **Creator_Role**: Kategori peran kreator berdasarkan performa (Superstar, Rising Star, Consistent Performer, Underperformer)
- **Revenue_Insight**: Analisis pendapatan yang menghubungkan kreator, produk, dan GMV yang dihasilkan
- **KPI**: Key Performance Indicator, metrik utama untuk mengukur kesuksesan kampanye
- **Dashboard**: Halaman utama yang menampilkan ringkasan KPI dan performa global
- **TikTok_Product_ID**: Identifier unik produk di platform TikTok

---

## Requirements

### Requirement 1: Penyimpanan Data Produk

**User Story:** Sebagai sistem, saya perlu menyimpan data produk yang dipromosikan, sehingga saya dapat menganalisis performa produk dan menghubungkannya dengan konten video yang mempromosikannya.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menyimpan data produk dengan field: nama produk, harga, kategori, dan TikTok_Product_ID
2. WHEN data produk disimpan, THE Platform_Analytics SHALL memvalidasi bahwa TikTok_Product_ID adalah string unik dan tidak kosong
3. WHEN data produk disimpan, THE Platform_Analytics SHALL memvalidasi bahwa harga adalah nilai numerik non-negatif
4. THE Platform_Analytics SHALL mendukung kategori produk sebagai array string untuk mengakomodasi produk multi-kategori

---

### Requirement 2: Penyimpanan Data Konten Video

**User Story:** Sebagai sistem, saya perlu menyimpan metrik performa konten video, sehingga saya dapat menganalisis efektivitas konten dan kontribusinya terhadap GMV.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menyimpan data Konten_Video dengan field: video_id, creator_id, product_id, views, likes, comments, shares, posted_at, dan gmv_generated
2. WHEN data Konten_Video disimpan, THE Platform_Analytics SHALL memvalidasi bahwa semua metrik numerik (views, likes, comments, shares, gmv_generated) adalah nilai non-negatif
3. THE Platform_Analytics SHALL menghubungkan setiap Konten_Video dengan tepat satu Kreator dan maksimal satu Produk melalui foreign key relationship
4. WHEN posted_at disimpan, THE Platform_Analytics SHALL memvalidasi bahwa timestamp tidak berada di masa depan

---

### Requirement 3: API Overview Global

**User Story:** Sebagai manajer pemasaran, saya ingin melihat KPI global kampanye, sehingga saya dapat memahami performa keseluruhan sistem secara sekilas.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menyediakan endpoint GET /api/v1/analytics/overview yang mengembalikan KPI global
2. WHEN endpoint overview dipanggil, THE Platform_Analytics SHALL menghitung dan mengembalikan: total_gmv, total_views, total_creators, global_conversion_rate, total_buyers, top_creator_name, top_creator_revenue, top_product_name, dan top_product_gmv
3. THE Platform_Analytics SHALL menghitung global_conversion_rate sebagai rasio total_buyers terhadap total unique viewers dari semua konten video
4. WHEN endpoint overview dipanggil, THE Platform_Analytics SHALL mengembalikan respons dalam waktu 3 detik untuk dataset hingga 100.000 konten video
5. THE Platform_Analytics SHALL mengidentifikasi top_creator sebagai kreator dengan estimated_revenue tertinggi
6. THE Platform_Analytics SHALL mengidentifikasi top_product sebagai produk dengan total_gmv tertinggi

---

### Requirement 4: API Creator Intelligence

**User Story:** Sebagai manajer pemasaran, saya ingin menganalisis performa kreator secara individual, sehingga saya dapat mengidentifikasi kreator berkinerja tinggi dan mengoptimalkan alokasi budget kampanye.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menyediakan endpoint GET /api/v1/analytics/creators yang mengembalikan daftar kreator dengan metrik performa
2. WHEN endpoint creators dipanggil, THE Platform_Analytics SHALL mengembalikan untuk setiap kreator: creator_id, name, total_videos, total_views, total_gmv, avg_engagement_rate, estimated_revenue, creator_score, dan creator_role
3. THE Platform_Analytics SHALL menghitung creator_score sebagai nilai komposit berdasarkan formula: (0.4 × normalized_gmv) + (0.3 × normalized_engagement) + (0.2 × normalized_consistency) + (0.1 × normalized_video_count)
4. THE Platform_Analytics SHALL mengklasifikasikan creator_role berdasarkan creator_score: Superstar (score >= 0.8), Rising Star (0.6 <= score < 0.8), Consistent Performer (0.4 <= score < 0.6), Underperformer (score < 0.4)
5. THE Platform_Analytics SHALL mendukung sorting hasil berdasarkan: revenue, views, engagement_rate, atau score
6. THE Platform_Analytics SHALL mendukung filtering hasil berdasarkan: min_score, creator_role, atau min_revenue
7. THE Platform_Analytics SHALL mendukung pagination dengan parameter limit dan offset

---

### Requirement 5: API Content Analytics

**User Story:** Sebagai manajer pemasaran, saya ingin menganalisis performa konten video secara individual, sehingga saya dapat memahami jenis konten yang paling efektif dalam menghasilkan GMV.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menyediakan endpoint GET /api/v1/analytics/content yang mengembalikan daftar konten video dengan metrik performa
2. WHEN endpoint content dipanggil, THE Platform_Analytics SHALL mengembalikan untuk setiap video: video_id, creator_id, creator_name, product_id, product_name, views, likes, comments, shares, engagement_rate, gmv_generated, conversion_rate, dan posted_at
3. THE Platform_Analytics SHALL menghitung engagement_rate untuk setiap video sebagai: ((likes + comments + shares) / views) × 100
4. THE Platform_Analytics SHALL menghitung conversion_rate untuk setiap video berdasarkan data transaksi yang terhubung dengan video tersebut
5. THE Platform_Analytics SHALL mendukung sorting hasil berdasarkan: views, engagement_rate, gmv, atau posted_at
6. THE Platform_Analytics SHALL mendukung filtering hasil berdasarkan: creator_id, product_id, min_views, atau date_range
7. THE Platform_Analytics SHALL mendukung pagination dengan parameter limit dan offset

---

### Requirement 6: API Product Analytics

**User Story:** Sebagai manajer pemasaran, saya ingin menganalisis performa produk yang dipromosikan, sehingga saya dapat mengidentifikasi produk yang paling menguntungkan dan mengoptimalkan strategi promosi produk.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menyediakan endpoint GET /api/v1/analytics/products yang mengembalikan daftar produk dengan metrik performa
2. WHEN endpoint products dipanggil, THE Platform_Analytics SHALL mengembalikan untuk setiap produk: product_id, name, category, price, total_videos, total_creators, total_views, total_gmv, avg_conversion_rate, dan total_buyers
3. THE Platform_Analytics SHALL menghitung total_videos sebagai jumlah konten video yang mempromosikan produk tersebut
4. THE Platform_Analytics SHALL menghitung total_creators sebagai jumlah kreator unik yang mempromosikan produk tersebut
5. THE Platform_Analytics SHALL menghitung avg_conversion_rate sebagai rata-rata conversion_rate dari semua video yang mempromosikan produk tersebut
6. THE Platform_Analytics SHALL mendukung sorting hasil berdasarkan: gmv, views, conversion_rate, atau total_creators
7. THE Platform_Analytics SHALL mendukung filtering hasil berdasarkan: category, min_gmv, atau min_conversion_rate
8. THE Platform_Analytics SHALL mendukung pagination dengan parameter limit dan offset

---

### Requirement 7: API Revenue Insights

**User Story:** Sebagai manajer pemasaran, saya ingin menganalisis hubungan antara kreator, produk, dan revenue yang dihasilkan, sehingga saya dapat mengidentifikasi kombinasi kreator-produk yang paling menguntungkan.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menyediakan endpoint GET /api/v1/analytics/revenue yang mengembalikan data revenue insights
2. WHEN endpoint revenue dipanggil, THE Platform_Analytics SHALL mengembalikan untuk setiap kombinasi kreator-produk: creator_id, creator_name, product_id, product_name, total_videos, total_gmv, avg_conversion_rate, dan revenue_contribution_percentage
3. THE Platform_Analytics SHALL menghitung revenue_contribution_percentage sebagai: (gmv_kombinasi_ini / total_gmv_semua_kombinasi) × 100
4. THE Platform_Analytics SHALL mendukung sorting hasil berdasarkan: gmv, conversion_rate, atau revenue_contribution
5. THE Platform_Analytics SHALL mendukung filtering hasil berdasarkan: creator_id, product_id, atau min_gmv
6. THE Platform_Analytics SHALL mendukung pagination dengan parameter limit dan offset

---

### Requirement 8: Dashboard Upgrade dengan KPI Global

**User Story:** Sebagai manajer pemasaran, saya ingin dashboard utama menampilkan KPI global dari analytics platform, sehingga saya dapat memantau performa keseluruhan sistem saat membuka aplikasi.

#### Acceptance Criteria

1. WHEN pengguna mengakses Dashboard, THE Platform_Analytics SHALL menampilkan empat KPI utama: Total GMV, Total Views, Total Kreator, dan Global Conversion Rate
2. THE Platform_Analytics SHALL mengambil data KPI dari endpoint /api/v1/analytics/overview
3. WHEN data KPI dimuat, THE Platform_Analytics SHALL menampilkan data dalam waktu 3 detik
4. THE Platform_Analytics SHALL menampilkan indikator loading saat data KPI sedang dimuat
5. WHEN KPI card diklik, THE Platform_Analytics SHALL menavigasi pengguna ke halaman analytics yang relevan (GMV → Revenue Insights, Views → Content Analytics, Kreator → Creator Intelligence)

---

### Requirement 9: Halaman Creator Intelligence

**User Story:** Sebagai manajer pemasaran, saya ingin halaman khusus untuk menganalisis performa kreator, sehingga saya dapat membuat keputusan tentang kolaborasi kreator berdasarkan data performa mereka.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menyediakan halaman Creator Intelligence yang menampilkan tabel kreator dengan kolom: nama, total videos, total views, engagement rate, estimated revenue, creator score, dan creator role
2. WHEN halaman Creator Intelligence dimuat, THE Platform_Analytics SHALL mengambil data dari endpoint /api/v1/analytics/creators
3. THE Platform_Analytics SHALL menampilkan badge visual untuk creator_role dengan warna berbeda: Superstar (emas), Rising Star (ungu), Consistent Performer (biru), Underperformer (abu-abu)
4. THE Platform_Analytics SHALL mendukung sorting tabel berdasarkan kolom yang dapat diklik
5. THE Platform_Analytics SHALL mendukung filtering kreator berdasarkan creator_role melalui dropdown filter
6. THE Platform_Analytics SHALL menampilkan pagination controls untuk navigasi antar halaman data

---

### Requirement 10: Halaman Content Analytics

**User Story:** Sebagai manajer pemasaran, saya ingin halaman khusus untuk menganalisis performa konten video, sehingga saya dapat memahami karakteristik konten yang menghasilkan GMV tinggi.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menyediakan halaman Content Analytics yang menampilkan tabel konten video dengan kolom: kreator, produk, views, engagement rate, GMV, conversion rate, dan tanggal posting
2. WHEN halaman Content Analytics dimuat, THE Platform_Analytics SHALL mengambil data dari endpoint /api/v1/analytics/content
3. THE Platform_Analytics SHALL menampilkan engagement_rate dengan color coding: hijau (>= 5%), kuning (2-5%), abu-abu (< 2%)
4. THE Platform_Analytics SHALL mendukung sorting tabel berdasarkan kolom yang dapat diklik
5. THE Platform_Analytics SHALL mendukung filtering konten berdasarkan kreator atau produk melalui dropdown filter
6. THE Platform_Analytics SHALL menampilkan pagination controls untuk navigasi antar halaman data

---

### Requirement 11: Halaman Product Analytics

**User Story:** Sebagai manajer pemasaran, saya ingin halaman khusus untuk menganalisis performa produk, sehingga saya dapat mengidentifikasi produk yang paling menguntungkan dan mengalokasikan budget promosi dengan lebih efektif.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menyediakan halaman Product Analytics yang menampilkan tabel produk dengan kolom: nama produk, kategori, harga, total videos, total kreator, total views, total GMV, avg conversion rate, dan total buyers
2. WHEN halaman Product Analytics dimuat, THE Platform_Analytics SHALL mengambil data dari endpoint /api/v1/analytics/products
3. THE Platform_Analytics SHALL menampilkan harga dan GMV dalam format mata uang Rupiah (Rp) dengan pemisah ribuan
4. THE Platform_Analytics SHALL mendukung sorting tabel berdasarkan kolom yang dapat diklik
5. THE Platform_Analytics SHALL mendukung filtering produk berdasarkan kategori melalui dropdown filter
6. THE Platform_Analytics SHALL menampilkan pagination controls untuk navigasi antar halaman data

---

### Requirement 12: Halaman Revenue Insights

**User Story:** Sebagai manajer pemasaran, saya ingin halaman khusus untuk menganalisis revenue berdasarkan kombinasi kreator-produk, sehingga saya dapat mengidentifikasi partnership yang paling menguntungkan.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menyediakan halaman Revenue Insights yang menampilkan tabel kombinasi kreator-produk dengan kolom: kreator, produk, total videos, total GMV, avg conversion rate, dan revenue contribution percentage
2. WHEN halaman Revenue Insights dimuat, THE Platform_Analytics SHALL mengambil data dari endpoint /api/v1/analytics/revenue
3. THE Platform_Analytics SHALL menampilkan revenue_contribution_percentage dengan visualisasi bar chart inline untuk memudahkan perbandingan
4. THE Platform_Analytics SHALL mendukung sorting tabel berdasarkan kolom yang dapat diklik
5. THE Platform_Analytics SHALL mendukung filtering berdasarkan kreator atau produk melalui dropdown filter
6. THE Platform_Analytics SHALL menampilkan pagination controls untuk navigasi antar halaman data

---

### Requirement 13: Sidebar Navigation Update

**User Story:** Sebagai pengguna, saya ingin sidebar navigation yang terorganisir dengan baik, sehingga saya dapat dengan mudah mengakses semua fitur analytics dan outreach.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menampilkan sidebar dengan tiga section: Analytics, Outreach, dan AI & Laporan
2. THE Platform_Analytics SHALL menampilkan section Analytics dengan menu items: Dashboard, Creator Intelligence, Content Analytics, Product Analytics, dan Revenue Insights
3. THE Platform_Analytics SHALL menampilkan section Outreach dengan menu items: Cari Affiliasi, Influencer, Kampanye, Template Pesan, dan Daftar Hitam
4. THE Platform_Analytics SHALL menampilkan section AI & Laporan dengan menu items: AI Learning dan Laporan
5. WHEN menu item diklik, THE Platform_Analytics SHALL menavigasi pengguna ke halaman yang sesuai
6. THE Platform_Analytics SHALL menandai menu item yang aktif dengan highlight visual yang berbeda

---

### Requirement 14: Perhitungan Creator Score

**User Story:** Sebagai sistem analytics, saya perlu menghitung creator score yang akurat, sehingga saya dapat memberikan penilaian objektif terhadap performa kreator.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menghitung creator_score menggunakan formula: (0.4 × normalized_gmv) + (0.3 × normalized_engagement) + (0.2 × normalized_consistency) + (0.1 × normalized_video_count)
2. WHEN menghitung normalized_gmv, THE Platform_Analytics SHALL menormalisasi total GMV kreator terhadap GMV tertinggi di dataset menggunakan min-max normalization ke rentang [0, 1]
3. WHEN menghitung normalized_engagement, THE Platform_Analytics SHALL menormalisasi rata-rata engagement_rate kreator terhadap engagement_rate tertinggi di dataset menggunakan min-max normalization ke rentang [0, 1]
4. WHEN menghitung normalized_consistency, THE Platform_Analytics SHALL menghitung standar deviasi GMV per video kreator, kemudian menormalisasi inverse standar deviasi (1 / (1 + std_dev)) ke rentang [0, 1]
5. WHEN menghitung normalized_video_count, THE Platform_Analytics SHALL menormalisasi jumlah video kreator terhadap jumlah video tertinggi di dataset menggunakan min-max normalization ke rentang [0, 1]
6. THE Platform_Analytics SHALL memastikan creator_score selalu berada dalam rentang [0, 1]

---

### Requirement 15: Agregasi Data Real-Time

**User Story:** Sebagai sistem analytics, saya perlu mengagregasi data dari berbagai tabel secara efisien, sehingga saya dapat menyajikan analytics dengan performa tinggi.

#### Acceptance Criteria

1. WHEN menghitung agregasi untuk endpoint analytics, THE Platform_Analytics SHALL menggunakan query SQL dengan JOIN dan GROUP BY untuk menghindari N+1 query problem
2. THE Platform_Analytics SHALL menggunakan index database pada kolom yang sering digunakan untuk filtering dan sorting (creator_id, product_id, posted_at, gmv_generated)
3. WHEN data analytics diminta dengan filter date_range, THE Platform_Analytics SHALL hanya memproses data dalam rentang tanggal yang diminta
4. THE Platform_Analytics SHALL menggunakan Redis cache untuk menyimpan hasil agregasi yang sering diminta dengan TTL 5 menit
5. WHEN cache tersedia untuk query yang sama, THE Platform_Analytics SHALL mengembalikan data dari cache tanpa melakukan query database ulang

---

### Requirement 16: Validasi Data Input

**User Story:** Sebagai sistem, saya perlu memvalidasi semua data input, sehingga saya dapat memastikan integritas data dan mencegah error perhitungan analytics.

#### Acceptance Criteria

1. WHEN data produk diterima, THE Platform_Analytics SHALL memvalidasi bahwa harga adalah nilai numerik positif dan kategori adalah array non-kosong
2. WHEN data konten video diterima, THE Platform_Analytics SHALL memvalidasi bahwa creator_id dan product_id merujuk ke record yang valid di database
3. WHEN data konten video diterima dengan metrik views bernilai 0, THE Platform_Analytics SHALL menetapkan engagement_rate dan conversion_rate ke 0 tanpa melakukan pembagian
4. IF data input tidak valid, THEN THE Platform_Analytics SHALL mengembalikan error response dengan kode HTTP 400 dan pesan error yang deskriptif
5. THE Platform_Analytics SHALL memvalidasi bahwa GMV yang diterima tidak melebihi batas maksimal yang wajar (misalnya 10 miliar Rupiah per video)

---

### Requirement 17: Handling Data Kosong

**User Story:** Sebagai pengguna, saya ingin sistem menangani kondisi data kosong dengan baik, sehingga saya tidak melihat error atau tampilan yang rusak saat belum ada data analytics.

#### Acceptance Criteria

1. WHEN endpoint analytics dipanggil dan tidak ada data yang tersedia, THE Platform_Analytics SHALL mengembalikan struktur response yang valid dengan nilai default (0 untuk numerik, array kosong untuk list)
2. WHEN halaman analytics dimuat dan tidak ada data yang tersedia, THE Platform_Analytics SHALL menampilkan pesan informatif "Belum ada data" atau "No data available"
3. WHEN menghitung creator_score untuk dataset kosong, THE Platform_Analytics SHALL mengembalikan score 0 tanpa menghasilkan error pembagian dengan nol
4. WHEN menghitung normalisasi dan semua nilai dalam dataset adalah sama, THE Platform_Analytics SHALL menetapkan semua nilai normalized ke 0.5

---

### Requirement 18: Format Response API Konsisten

**User Story:** Sebagai frontend developer, saya ingin semua endpoint analytics mengembalikan format response yang konsisten, sehingga saya dapat memproses data dengan mudah dan mengurangi error handling.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL mengembalikan semua response API dalam format JSON dengan struktur: { "data": [...], "meta": {...} }
2. WHEN endpoint mendukung pagination, THE Platform_Analytics SHALL menyertakan meta pagination dengan field: page, page_size, total_items, dan total_pages
3. WHEN endpoint mengembalikan list kosong, THE Platform_Analytics SHALL mengembalikan array kosong dalam field data, bukan null
4. IF error terjadi saat memproses request, THEN THE Platform_Analytics SHALL mengembalikan response dengan struktur: { "error": { "code": str, "message": str, "details": {...} } }
5. THE Platform_Analytics SHALL menggunakan snake_case untuk semua field name dalam response JSON

---

### Requirement 19: Migration Database untuk Analytics

**User Story:** Sebagai sistem, saya perlu skema database yang mendukung penyimpanan data analytics, sehingga saya dapat menyimpan dan mengquery data produk dan konten video dengan efisien.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menyediakan migration script yang membuat tabel products dengan kolom: id, name, price, category, tiktok_product_id, created_at, updated_at
2. THE Platform_Analytics SHALL menyediakan migration script yang membuat tabel content_videos dengan kolom: id, video_id, creator_id, product_id, views, likes, comments, shares, posted_at, gmv_generated, created_at, updated_at
3. THE Platform_Analytics SHALL membuat foreign key constraint dari content_videos.creator_id ke influencers.id
4. THE Platform_Analytics SHALL membuat foreign key constraint dari content_videos.product_id ke products.id dengan ON DELETE SET NULL
5. THE Platform_Analytics SHALL membuat index pada content_videos(creator_id, posted_at) untuk optimasi query analytics
6. THE Platform_Analytics SHALL membuat index pada content_videos(product_id, gmv_generated) untuk optimasi query analytics
7. THE Platform_Analytics SHALL membuat unique constraint pada products(tiktok_product_id) untuk mencegah duplikasi produk

---

### Requirement 20: Integrasi dengan Sistem Existing

**User Story:** Sebagai sistem, saya perlu terintegrasi dengan sistem influencer marketing yang sudah ada, sehingga saya dapat menggunakan data kreator dan kampanye yang sudah tersimpan.

#### Acceptance Criteria

1. THE Platform_Analytics SHALL menggunakan tabel influencers yang sudah ada sebagai sumber data kreator
2. THE Platform_Analytics SHALL menggunakan tabel campaigns yang sudah ada untuk menghubungkan konten video dengan kampanye
3. WHEN mengambil data kreator untuk analytics, THE Platform_Analytics SHALL mengecualikan kreator dengan status BLACKLISTED
4. THE Platform_Analytics SHALL menggunakan connection pool database yang sama dengan sistem existing untuk menghindari connection exhaustion
5. THE Platform_Analytics SHALL menggunakan async/await pattern yang konsisten dengan kode existing untuk semua operasi database
