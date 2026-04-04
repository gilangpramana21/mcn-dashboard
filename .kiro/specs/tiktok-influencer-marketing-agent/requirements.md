# Dokumen Requirements

## Pendahuluan

Sistem Agen Cerdas Pemasaran Influencer TikTok adalah alat pemasaran otomatis yang menyederhanakan dan mengoptimalkan keseluruhan proses pemasaran influencer TikTok. Sistem ini terintegrasi dengan platform Affiliate Center Indonesia dan mewujudkan manajemen otomatis penuh dari proses seleksi influencer, undangan massal, pemantauan konten, dan klasifikasi umpan balik.

Sistem ini dirancang untuk membantu tim pemasaran mengelola ratusan hingga ribuan influencer secara efisien, mengurangi pekerjaan manual, dan meningkatkan efektivitas kampanye pemasaran melalui otomasi berbasis agen cerdas.

## Glosarium

- **Sistem**: Sistem Agen Cerdas Pemasaran Influencer TikTok secara keseluruhan
- **Agen**: Komponen agen cerdas otomatis yang menjalankan tugas-tugas pemasaran
- **Influencer**: Kreator konten TikTok yang memiliki jumlah pengikut dan tingkat keterlibatan tertentu
- **Affiliate_Center**: Platform Affiliate Center Indonesia yang menjadi sumber data dan target integrasi
- **Kampanye**: Serangkaian aktivitas pemasaran yang dijalankan dalam periode waktu tertentu
- **Undangan**: Pesan yang dikirimkan kepada influencer untuk bergabung dalam kampanye
- **Konten**: Video atau postingan TikTok yang dibuat oleh influencer sebagai bagian dari kampanye
- **Umpan_Balik**: Respons atau reaksi influencer terhadap undangan yang dikirimkan
- **Selektor**: Komponen yang bertanggung jawab memfilter dan memilih influencer berdasarkan kriteria
- **Pengirim**: Komponen yang bertanggung jawab mengirimkan undangan kepada influencer
- **Monitor**: Komponen yang bertanggung jawab memantau konten yang diterbitkan influencer
- **Pengklasifikasi**: Komponen yang bertanggung jawab mengklasifikasikan umpan balik influencer
- **Dasbor**: Antarmuka pengguna utama untuk memantau dan mengelola kampanye
- **GMV**: Gross Merchandise Value, total nilai transaksi yang dihasilkan dari kampanye
- **Pengumpul_WhatsApp**: Komponen yang bertanggung jawab mengumpulkan nomor WhatsApp affiliate secara otomatis melalui tiga metode bertingkat
- **Bio_Profil**: Teks deskripsi profil affiliate yang tercantum di TikTok Seller Center
- **Ikon_WhatsApp_Resmi**: Tombol atau ikon WhatsApp yang terdaftar secara resmi pada profil affiliate di TikTok Seller Center
- **Pola_Nomor_WA**: Format penulisan nomor WhatsApp yang umum digunakan dalam teks bio, seperti wa.me/628xxx, +62812xxx, WA: 0812xxx, dan variasinya

---

## Requirements

### Requirement 1: Integrasi dengan Affiliate Center Indonesia

**User Story:** Sebagai manajer pemasaran, saya ingin sistem terhubung dengan Affiliate Center Indonesia, sehingga saya dapat mengakses data influencer secara real-time tanpa input manual.

#### Acceptance Criteria

1. THE Sistem SHALL terhubung dengan API Affiliate Center Indonesia menggunakan autentikasi OAuth 2.0
2. WHEN koneksi ke Affiliate Center gagal, THE Sistem SHALL mencoba kembali koneksi sebanyak 3 kali dengan interval 5 detik sebelum menampilkan pesan kesalahan
3. WHEN data influencer diperbarui di Affiliate Center, THE Sistem SHALL menyinkronkan data tersebut dalam waktu 15 menit
4. IF token autentikasi kedaluwarsa, THEN THE Sistem SHALL memperbarui token secara otomatis tanpa interupsi sesi pengguna
5. THE Sistem SHALL mendukung pagination saat mengambil daftar influencer dengan batas maksimal 100 data per permintaan

---

### Requirement 2: Seleksi Influencer Otomatis

**User Story:** Sebagai manajer pemasaran, saya ingin sistem secara otomatis memfilter dan memilih influencer berdasarkan kriteria yang saya tentukan, sehingga saya dapat menemukan influencer yang paling relevan untuk kampanye saya.

#### Acceptance Criteria

1. THE Selektor SHALL memfilter influencer berdasarkan minimal satu dari kriteria berikut: jumlah pengikut, tingkat keterlibatan (engagement rate), kategori konten, dan lokasi geografis
2. WHEN kriteria seleksi diterapkan, THE Selektor SHALL menampilkan hasil dalam waktu 10 detik untuk dataset hingga 10.000 influencer
3. THE Selektor SHALL menghitung skor relevansi untuk setiap influencer berdasarkan bobot kriteria yang dikonfigurasi oleh pengguna
4. WHILE proses seleksi berjalan, THE Selektor SHALL menampilkan indikator progres kepada pengguna
5. IF tidak ada influencer yang memenuhi kriteria seleksi, THEN THE Selektor SHALL menampilkan pesan informatif dan menyarankan pelonggaran kriteria
6. THE Selektor SHALL menyimpan konfigurasi kriteria seleksi sebagai template yang dapat digunakan kembali

---

### Requirement 3: Undangan Massal Otomatis

**User Story:** Sebagai manajer pemasaran, saya ingin sistem mengirimkan undangan secara massal kepada influencer yang telah dipilih, sehingga saya dapat menghemat waktu dan memastikan konsistensi pesan.

#### Acceptance Criteria

1. THE Pengirim SHALL mengirimkan undangan kepada daftar influencer yang dipilih melalui kanal komunikasi yang tersedia di Affiliate Center
2. WHEN undangan massal dimulai, THE Pengirim SHALL mengirimkan undangan dengan laju maksimal 100 undangan per menit untuk menghindari pembatasan API
3. WHEN setiap undangan berhasil dikirim, THE Pengirim SHALL mencatat status pengiriman beserta timestamp
4. IF pengiriman undangan kepada satu influencer gagal, THEN THE Pengirim SHALL mencatat kegagalan tersebut dan melanjutkan pengiriman kepada influencer berikutnya
5. THE Pengirim SHALL mendukung personalisasi pesan undangan dengan variabel dinamis seperti nama influencer dan detail kampanye
6. WHEN seluruh proses pengiriman selesai, THE Pengirim SHALL menghasilkan laporan ringkasan yang mencakup jumlah berhasil, gagal, dan tertunda
7. THE Pengirim SHALL mendukung penjadwalan pengiriman undangan pada waktu yang ditentukan pengguna

---

### Requirement 4: Pemantauan Konten Influencer

**User Story:** Sebagai manajer pemasaran, saya ingin sistem memantau konten yang diterbitkan oleh influencer secara otomatis, sehingga saya dapat memastikan konten sesuai dengan panduan kampanye dan melacak performa.

#### Acceptance Criteria

1. WHILE kampanye aktif, THE Monitor SHALL memeriksa konten baru dari influencer yang berpartisipasi setiap 30 menit
2. WHEN konten baru diterbitkan oleh influencer, THE Monitor SHALL mengekstrak metrik performa meliputi jumlah tayangan, suka, komentar, dan berbagi
3. THE Monitor SHALL mendeteksi apakah konten mengandung tautan afiliasi yang valid sesuai dengan kampanye yang berjalan
4. IF konten influencer tidak memenuhi panduan kampanye yang ditetapkan, THEN THE Monitor SHALL mengirimkan notifikasi kepada manajer pemasaran dalam waktu 1 jam setelah konten terdeteksi
5. THE Monitor SHALL menyimpan riwayat metrik performa konten dengan granularitas harian selama periode kampanye berlangsung
6. WHEN kampanye berakhir, THE Monitor SHALL menghasilkan laporan performa akhir yang mencakup total tayangan, total GMV, dan tingkat konversi per influencer

---

### Requirement 5: Klasifikasi Umpan Balik Otomatis

**User Story:** Sebagai manajer pemasaran, saya ingin sistem mengklasifikasikan umpan balik dari influencer secara otomatis, sehingga saya dapat memprioritaskan tindak lanjut dengan tepat.

#### Acceptance Criteria

1. WHEN umpan balik diterima dari influencer, THE Pengklasifikasi SHALL mengklasifikasikan umpan balik ke dalam kategori: Menerima, Menolak, Membutuhkan_Informasi_Lebih_Lanjut, atau Tidak_Merespons
2. THE Pengklasifikasi SHALL memproses setiap umpan balik dalam waktu 60 detik setelah diterima
3. WHEN umpan balik diklasifikasikan sebagai Membutuhkan_Informasi_Lebih_Lanjut, THE Pengklasifikasi SHALL menandai umpan balik tersebut untuk ditindaklanjuti oleh tim pemasaran
4. IF umpan balik tidak dapat diklasifikasikan secara otomatis dengan tingkat kepercayaan di atas 80%, THEN THE Pengklasifikasi SHALL mengalihkan umpan balik tersebut ke antrian tinjauan manual
5. THE Pengklasifikasi SHALL menghasilkan ringkasan distribusi klasifikasi umpan balik per kampanye
6. WHEN influencer diklasifikasikan sebagai Menolak, THE Pengklasifikasi SHALL memperbarui status influencer tersebut dalam daftar kampanye secara otomatis

---

### Requirement 6: Dasbor Manajemen Kampanye

**User Story:** Sebagai manajer pemasaran, saya ingin memiliki dasbor terpusat untuk memantau semua aktivitas kampanye, sehingga saya dapat membuat keputusan berdasarkan data secara cepat.

#### Acceptance Criteria

1. THE Dasbor SHALL menampilkan ringkasan status kampanye aktif meliputi jumlah influencer yang diundang, menerima, menolak, dan menghasilkan konten
2. WHEN pengguna mengakses Dasbor, THE Dasbor SHALL memuat data terkini dalam waktu 3 detik
3. THE Dasbor SHALL menampilkan grafik tren performa kampanye dengan rentang waktu yang dapat dikonfigurasi: 7 hari, 30 hari, atau kustom
4. WHEN metrik kampanye melampaui ambang batas yang dikonfigurasi, THE Dasbor SHALL menampilkan notifikasi peringatan kepada pengguna
5. THE Dasbor SHALL mendukung ekspor data kampanye dalam format CSV dan Excel
6. WHERE fitur multi-kampanye diaktifkan, THE Dasbor SHALL menampilkan perbandingan performa antar kampanye secara berdampingan

---

### Requirement 7: Manajemen Template Pesan

**User Story:** Sebagai manajer pemasaran, saya ingin mengelola template pesan undangan, sehingga saya dapat memastikan konsistensi komunikasi dan menghemat waktu pembuatan pesan.

#### Acceptance Criteria

1. THE Sistem SHALL mendukung pembuatan, pengeditan, dan penghapusan template pesan undangan
2. WHEN template pesan disimpan, THE Sistem SHALL memvalidasi bahwa semua variabel dinamis dalam template memiliki nilai default yang valid
3. IF template pesan dihapus sementara masih digunakan oleh kampanye aktif, THEN THE Sistem SHALL menampilkan peringatan konfirmasi sebelum menghapus
4. THE Sistem SHALL mendukung pratinjau template pesan dengan data influencer sampel sebelum digunakan dalam kampanye
5. THE Sistem SHALL menyimpan riwayat versi template pesan sehingga pengguna dapat mengembalikan ke versi sebelumnya

---

### Requirement 8: Pengelolaan Daftar Hitam Influencer

**User Story:** Sebagai manajer pemasaran, saya ingin mengelola daftar hitam influencer, sehingga saya dapat mencegah pengiriman undangan kepada influencer yang tidak sesuai atau bermasalah.

#### Acceptance Criteria

1. THE Sistem SHALL memungkinkan pengguna menambahkan influencer ke daftar hitam beserta alasan yang tercatat
2. WHEN proses seleksi influencer berjalan, THE Selektor SHALL secara otomatis mengecualikan influencer yang terdapat dalam daftar hitam
3. IF pengguna mencoba mengirim undangan kepada influencer yang ada dalam daftar hitam, THEN THE Pengirim SHALL menolak pengiriman dan menampilkan alasan pemblokiran
4. THE Sistem SHALL mendukung penghapusan influencer dari daftar hitam dengan pencatatan alasan penghapusan
5. THE Sistem SHALL menghasilkan laporan daftar hitam yang dapat diekspor dalam format CSV

---

### Requirement 9: Keamanan dan Kontrol Akses

**User Story:** Sebagai administrator sistem, saya ingin mengontrol akses pengguna ke fitur-fitur sistem, sehingga saya dapat memastikan keamanan data dan pembagian tanggung jawab yang tepat.

#### Acceptance Criteria

1. THE Sistem SHALL mendukung autentikasi pengguna menggunakan kombinasi nama pengguna dan kata sandi dengan panjang minimal 8 karakter
2. THE Sistem SHALL menerapkan kontrol akses berbasis peran dengan minimal tiga peran: Administrator, Manajer_Kampanye, dan Peninjau
3. WHILE sesi pengguna tidak aktif selama 30 menit, THE Sistem SHALL mengakhiri sesi secara otomatis dan meminta autentikasi ulang
4. THE Sistem SHALL mencatat semua aktivitas pengguna yang berkaitan dengan pengelolaan kampanye dan pengiriman undangan dalam log audit
5. IF percobaan login gagal sebanyak 5 kali berturut-turut, THEN THE Sistem SHALL mengunci akun selama 15 menit dan mengirimkan notifikasi kepada administrator

---

### Requirement 10: Pelaporan dan Analitik

**User Story:** Sebagai manajer pemasaran, saya ingin menghasilkan laporan komprehensif tentang performa kampanye, sehingga saya dapat menganalisis ROI dan mengoptimalkan strategi pemasaran berikutnya.

#### Acceptance Criteria

1. THE Sistem SHALL menghasilkan laporan performa kampanye yang mencakup metrik: total influencer, tingkat penerimaan undangan, total tayangan, total GMV, dan biaya per konversi
2. WHEN laporan diminta, THE Sistem SHALL menghasilkan laporan dalam waktu 30 detik untuk data kampanye hingga 12 bulan
3. THE Sistem SHALL mendukung pemfilteran laporan berdasarkan rentang tanggal, kategori influencer, dan status kampanye
4. THE Sistem SHALL mendukung ekspor laporan dalam format PDF, CSV, dan Excel
5. WHERE fitur analitik lanjutan diaktifkan, THE Sistem SHALL menampilkan analisis prediktif performa influencer berdasarkan data historis kampanye sebelumnya

---

### Requirement 11: Pengumpulan Nomor WhatsApp Affiliate Secara Otomatis

**User Story:** Sebagai manajer pemasaran, saya ingin sistem secara otomatis mengumpulkan nomor WhatsApp affiliate melalui tiga metode bertingkat, sehingga saya dapat mengirimkan undangan kampanye via WhatsApp tanpa harus mencari nomor secara manual.

#### Acceptance Criteria

1. WHEN sistem membutuhkan nomor WhatsApp affiliate, THE Pengumpul_WhatsApp SHALL terlebih dahulu memeriksa Bio_Profil affiliate di TikTok Seller Center untuk mendeteksi keberadaan Ikon_WhatsApp_Resmi yang terdaftar pada profil
2. WHEN Ikon_WhatsApp_Resmi ditemukan pada profil affiliate, THE Pengumpul_WhatsApp SHALL mengekstrak nomor WhatsApp dari ikon tersebut dan menyimpannya ke profil influencer di database tanpa melanjutkan ke metode berikutnya
3. IF Ikon_WhatsApp_Resmi tidak ditemukan pada profil affiliate, THEN THE Pengumpul_WhatsApp SHALL mem-parse teks Bio_Profil secara otomatis untuk mendeteksi Pola_Nomor_WA yang ditulis oleh affiliate, mencakup format: wa.me/628xxx, +62812xxx, WA: 0812xxx, 0812xxx, dan variasi penulisan nomor Indonesia lainnya
4. WHEN Pola_Nomor_WA berhasil ditemukan dalam teks Bio_Profil, THE Pengumpul_WhatsApp SHALL mengekstrak dan menormalisasi nomor tersebut ke format internasional (+62) lalu menyimpannya ke profil influencer di database tanpa melanjutkan ke metode berikutnya
5. IF Pola_Nomor_WA tidak ditemukan dalam teks Bio_Profil, THEN THE Pengumpul_WhatsApp SHALL mengirimkan pesan otomatis melalui fitur chat TikTok Seller Center kepada affiliate untuk menanyakan nomor WhatsApp
6. WHEN affiliate membalas pesan chat dengan nomor WhatsApp, THE Pengumpul_WhatsApp SHALL mengekstrak nomor dari teks balasan secara otomatis, menormalisasi ke format internasional (+62), dan menyimpannya ke profil influencer di database
7. THE Pengumpul_WhatsApp SHALL mencatat metode pengumpulan yang berhasil digunakan (ikon resmi, parsing bio, atau balasan chat) beserta timestamp pada setiap profil influencer
8. WHEN nomor WhatsApp berhasil tersimpan ke profil influencer melalui salah satu dari tiga metode, THE Pengirim SHALL menggunakan nomor tersebut sebagai kanal pengiriman undangan kampanye berikutnya
9. IF affiliate tidak membalas pesan chat dalam waktu 48 jam, THEN THE Pengumpul_WhatsApp SHALL menandai status pengumpulan nomor WhatsApp affiliate tersebut sebagai tidak_tersedia dan mencatatnya dalam log
10. THE Pengumpul_WhatsApp SHALL memvalidasi bahwa nomor WhatsApp yang diekstrak dari ketiga metode merupakan nomor valid dengan format yang dapat dihubungi sebelum menyimpan ke database

---

### Requirement 12: Dashboard Pencarian dan Detail Affiliate

**User Story:** Sebagai manajer pemasaran, saya ingin dapat mencari dan melihat detail affiliate langsung dari dashboard, sehingga saya dapat menemukan affiliate yang tepat dan menghubungi mereka dengan cepat melalui kanal yang tersedia.

#### Acceptance Criteria

1. THE Dasbor SHALL menyediakan fitur pencarian dan filter affiliate berdasarkan minimal satu dari kriteria berikut: jumlah pengikut, engagement rate, kategori konten, dan lokasi geografis
2. WHEN kriteria pencarian diterapkan, THE Dasbor SHALL menampilkan daftar affiliate yang memenuhi semua kriteria yang dipilih dalam waktu 10 detik
3. WHEN pengguna mengklik salah satu affiliate dari daftar hasil pencarian, THE Dasbor SHALL menampilkan halaman atau panel detail yang memuat seluruh data affiliate tersebut
4. WHEN halaman detail affiliate ditampilkan dan affiliate memiliki nomor WhatsApp yang tersimpan di database atau terdeteksi dari Ikon_WhatsApp_Resmi atau Bio_Profil, THE Dasbor SHALL menampilkan tombol untuk mengirim pesan otomatis kepada affiliate melalui WhatsApp
5. IF affiliate tidak memiliki nomor WhatsApp yang tersimpan maupun yang dapat dideteksi, THEN THE Dasbor SHALL menampilkan tombol untuk mengirim pesan kepada affiliate melalui fitur chat TikTok Seller Center guna menanyakan nomor WhatsApp
6. WHEN affiliate membalas pesan chat dengan nomor WhatsApp, THE Pengumpul_WhatsApp SHALL mengekstrak nomor tersebut secara otomatis dan menyimpannya ke profil affiliate di database

---

### Requirement 13: Self-Improving AI Agent (Pembelajaran Berkelanjutan)

**User Story:** Sebagai manajer pemasaran, saya ingin sistem AI semakin akurat seiring penggunaan, sehingga rekomendasi influencer dan klasifikasi umpan balik terus meningkat kualitasnya berdasarkan data historis kampanye.

#### Acceptance Criteria

1. THE Sistem SHALL meningkatkan akurasi model seleksi influencer secara berkelanjutan berdasarkan data performa historis kampanye, mencakup tingkat konversi, GMV yang dihasilkan, dan tingkat penerimaan undangan per influencer
2. WHEN kampanye selesai, THE Sistem SHALL memperbarui model seleksi influencer menggunakan data hasil kampanye tersebut sebagai umpan balik untuk siklus pembelajaran berikutnya
3. THE Pengklasifikasi SHALL meningkatkan akurasi klasifikasi umpan balik secara berkelanjutan berdasarkan data umpan balik yang telah diklasifikasikan sebelumnya, termasuk hasil tinjauan manual
4. THE Sistem SHALL menghasilkan rekomendasi influencer yang diprediksi akan memberikan performa tinggi berdasarkan pola data historis kampanye sebelumnya
5. WHILE proses pembelajaran berlangsung, THE Sistem SHALL menjalankan pembaruan model di background tanpa mengganggu operasi kampanye yang sedang aktif
6. WHEN model seleksi diperbarui, THE Sistem SHALL mencatat versi model, timestamp pembaruan, dan metrik akurasi sebelum serta sesudah pembaruan dalam log sistem
