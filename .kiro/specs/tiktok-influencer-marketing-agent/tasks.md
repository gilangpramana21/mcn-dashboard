# Rencana Implementasi: Sistem Agen Cerdas Pemasaran Influencer TikTok

## Overview

Implementasi dilakukan secara bertahap mengikuti arsitektur multi-agen: dimulai dari fondasi (model data, konfigurasi, infrastruktur), kemudian setiap agen secara berurutan, diikuti lapisan API, dan diakhiri dengan integrasi penuh.

Bahasa: Python | Framework: FastAPI | Database: PostgreSQL | Cache/Queue: Redis Streams | Testing: pytest + hypothesis

---

## Tasks

- [x] 1. Setup struktur proyek, konfigurasi, dan model data inti
  - Buat struktur direktori proyek: `app/`, `app/agents/`, `app/services/`, `app/integrations/`, `app/api/`, `app/models/`, `tests/unit/`, `tests/property/`, `tests/integration/`
  - Buat `pyproject.toml` / `requirements.txt` dengan dependensi: fastapi, uvicorn, sqlalchemy, asyncpg, redis, tenacity, hypothesis, pytest, pytest-asyncio, pytest-mock, python-jose, passlib
  - Buat `app/models/domain.py` dengan semua dataclass dan Enum: `Campaign`, `CampaignStatus`, `CampaignSettings`, `Influencer`, `InfluencerStatus`, `SelectionCriteria`, `CriteriaWeights`, `Invitation`, `InvitationStatus`, `ContentMetrics`, `InfluencerFeedback`, `FeedbackCategory`, `MessageTemplate`, `User`, `UserRole`, `WhatsAppCollectionRecord`, `WhatsAppCollectionMethod`, `WhatsAppCollectionStatus`, `WhatsAppCollectionResult`, `AffiliateCard`, `AffiliateDetail`, `ModelVersion`, `ModelType`, `InfluencerRecommendation`, `CampaignOutcome`
  - Buat `app/exceptions.py` dengan hierarki exception lengkap sesuai desain
  - Buat `app/config.py` dengan konfigurasi environment (database URL, Redis URL, API keys, JWT secret)
  - Buat `app/database.py` dengan setup SQLAlchemy async engine dan session factory
  - Buat `app/db/migrations/` dengan skema SQL awal untuk semua tabel dan indeks
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1, 11.1_

- [x] 2. Implementasi lapisan integrasi eksternal
  - [x] 2.1 Implementasi `AffiliateCenterClient` di `app/integrations/affiliate_center.py`
    - Implementasi `authenticate()`, `refresh_token()`, `get_influencers()` dengan pagination (max 100/halaman), `sync_influencer_data()`
    - Terapkan decorator `@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))` pada semua method yang memanggil API
    - Implementasi auto-refresh token saat `TokenExpiredError` terdeteksi
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 2.2 Tulis property test untuk AffiliateCenterClient
    - **Property 1: Retry Koneksi Tepat 3 Kali** — verifikasi retry tepat 3x sebelum raise error
    - **Property 2: Token Refresh Transparan** — verifikasi request dengan token expired diselesaikan tanpa error ke pemanggil
    - **Property 3: Pagination Tidak Melebihi Batas** — verifikasi setiap halaman ≤ 100 item
    - **Validates: Requirements 1.2, 1.4, 1.5**

  - [x] 2.3 Implementasi `TikTokAPIClient` di `app/integrations/tiktok_api.py`
    - Implementasi `get_user_videos()` dan `get_video_metrics()`
    - Implementasi circuit breaker: open setelah 5 kegagalan dalam 60 detik, half-open setelah 30 detik
    - _Requirements: 4.1, 4.2, 11.1_

  - [x] 2.4 Implementasi `WhatsAppAPIClient` di `app/integrations/whatsapp_api.py`
    - Implementasi `send_message()` dan `get_message_status()`
    - Terapkan circuit breaker yang sama seperti TikTok client
    - _Requirements: 3.1, 11.5_

- [x] 3. Implementasi Auth Service dan RBAC
  - [x] 3.1 Implementasi `AuthService` di `app/services/auth_service.py`
    - Implementasi registrasi dan login dengan validasi panjang password minimal 8 karakter
    - Implementasi JWT token generation dan validasi dengan `python-jose`
    - Implementasi session timeout 30 menit (validasi `last_activity_at`)
    - Implementasi penguncian akun setelah 5 kali gagal login (kunci 15 menit)
    - Implementasi RBAC middleware: `Administrator`, `Manajer_Kampanye`, `Peninjau`
    - Implementasi audit log writer untuk setiap operasi kampanye dan undangan
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 3.2 Tulis property test untuk AuthService
    - **Property 28: Validasi Panjang Kata Sandi** — password < 8 karakter selalu ditolak
    - **Property 29: Kontrol Akses Berbasis Peran** — operasi terbatas mengembalikan 403 untuk peran tidak berwenang
    - **Property 30: Audit Log untuk Setiap Operasi Kampanye** — setiap operasi kampanye/undangan menghasilkan entri audit log
    - **Property 31: Penguncian Akun Setelah 5 Kali Gagal Login** — akun terkunci setelah 5 kali gagal berturut-turut
    - **Validates: Requirements 9.1, 9.2, 9.4, 9.5**

  - [x] 3.3 Tulis unit test untuk AuthService
    - Test edge case: login dengan akun terkunci, session timeout, refresh token expired
    - _Requirements: 9.1, 9.2, 9.3, 9.5_

- [x] 4. Checkpoint — Pastikan semua test lulus
  - Pastikan semua test lulus, tanyakan kepada pengguna jika ada pertanyaan.

- [x] 5. Implementasi Blacklist Service dan Template Service
  - [x] 5.1 Implementasi `BlacklistService` di `app/services/blacklist_service.py`
    - Implementasi `add_to_blacklist()`, `remove_from_blacklist()`, `is_blacklisted()`, `export_blacklist_csv()`
    - Pastikan `is_blacklisted()` digunakan oleh SelectorAgent dan SenderAgent
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 5.2 Tulis property test untuk BlacklistService
    - **Property 25: Blacklist Round-Trip** — influencer yang ditambahkan dengan alasan tertentu dapat diambil kembali dengan alasan yang sama
    - **Property 26: Seleksi Mengecualikan Blacklist** — tidak ada influencer blacklisted dalam hasil seleksi
    - **Property 27: Pengiriman Menolak Influencer Blacklist** — pengiriman ke influencer blacklisted selalu ditolak dengan error
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**

  - [x] 5.3 Implementasi `TemplateService` di `app/services/template_service.py`
    - Implementasi CRUD template: `create()`, `update()`, `delete()`, `get()`
    - Implementasi validasi variabel: semua `{{variable}}` dalam konten harus ada di `default_values`
    - Implementasi versioning: setiap update menyimpan versi lama, nomor versi bertambah monoton
    - Implementasi `preview()`: substitusi variabel dengan data influencer sampel
    - Implementasi guard saat `delete()` dipanggil pada template yang digunakan kampanye aktif (raise `TemplateInUseError`)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 5.4 Tulis property test untuk TemplateService
    - **Property 22: Validasi Variabel Template** — semua variabel dalam konten template memiliki default_values tidak kosong
    - **Property 23: Pratinjau Template Tersubstitusi** — pratinjau tidak mengandung placeholder `{{...}}` yang belum disubstitusi
    - **Property 24: Riwayat Versi Template** — nomor versi bertambah monoton setiap update, versi lama tetap dapat diakses
    - **Validates: Requirements 7.2, 7.4, 7.5**

- [x] 6. Implementasi Selector Agent
  - [x] 6.1 Implementasi `SelectorAgent` di `app/agents/selector_agent.py`
    - Implementasi `select_influencers()`: filter berdasarkan `min_followers`, `max_followers`, `min_engagement_rate`, `content_categories`, `locations`
    - Implementasi `calculate_relevance_score()`: hitung skor [0.0, 1.0] berdasarkan `CriteriaWeights` (deterministik)
    - Integrasikan `BlacklistService.is_blacklisted()` untuk mengecualikan influencer blacklisted
    - Implementasi `save_criteria_template()` untuk menyimpan konfigurasi sebagai template yang dapat digunakan kembali
    - Tampilkan pesan informatif dan saran pelonggaran kriteria jika hasil seleksi kosong
    - Publish event ke Redis Streams setelah seleksi selesai
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 8.2_

  - [x] 6.2 Tulis property test untuk SelectorAgent
    - **Property 4: Hasil Seleksi Memenuhi Semua Kriteria** — setiap influencer dalam hasil memenuhi semua kriteria yang diterapkan
    - **Property 5: Skor Relevansi Konsisten dan Terbatas** — skor selalu dalam [0.0, 1.0] dan deterministik untuk input yang sama
    - **Property 6: Template Kriteria Round-Trip** — template yang disimpan dan diambil kembali menghasilkan data identik
    - **Property 26: Seleksi Mengecualikan Blacklist** — tidak ada influencer blacklisted dalam hasil seleksi
    - **Validates: Requirements 2.1, 2.3, 2.6, 8.2**

  - [x] 6.3 Tulis unit test untuk SelectorAgent
    - Test edge case: dataset kosong, semua influencer di-blacklist, tidak ada yang memenuhi kriteria
    - _Requirements: 2.5_

- [x] 7. Implementasi WhatsApp Collector Agent
  - [x] 7.1 Implementasi `WhatsAppCollectorAgent` di `app/agents/whatsapp_collector_agent.py`
    - Implementasi `normalize_to_e164()`: normalisasi format 08xxx, +628xxx, 628xxx, wa.me/628xxx, WA: 08xxx ke format E.164
    - Implementasi `validate_whatsapp_number()`: validasi format `+62` diikuti 9–12 digit
    - Implementasi `check_official_whatsapp_icon()`: panggil TikTok Seller Center API untuk cek ikon resmi
    - Implementasi `parse_bio_for_whatsapp()`: regex parsing teks bio untuk pola nomor WA Indonesia
    - Implementasi `send_chat_request()`: kirim pesan otomatis via chat TikTok Seller Center
    - Implementasi `monitor_chat_reply()`: polling balasan chat dengan timeout 48 jam
    - Implementasi `collect_whatsapp_number()`: orkestrasi tiga metode secara berurutan (ikon → bio → chat), berhenti di metode pertama yang berhasil
    - Implementasi `save_collection_record()`: simpan nomor + method + timestamp ke database, tolak nomor tidak valid dengan `InvalidPhoneNumberError`
    - Implementasi `mark_unavailable()`: set status `unavailable` jika semua metode gagal atau timeout
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.9, 11.10_

  - [x] 7.2 Tulis property test untuk WhatsAppCollectorAgent
    - **Property 34: Urutan Prioritas Metode Pengumpulan WhatsApp** — metode selalu dicoba berurutan, metode berikutnya tidak dipanggil jika metode sebelumnya berhasil
    - **Property 35: Normalisasi Nomor ke Format E.164** — semua format nomor Indonesia valid menghasilkan `+62` + digit yang sama
    - **Property 36: Hanya Nomor Valid yang Tersimpan ke Database** — nomor tidak valid selalu raise `InvalidPhoneNumberError` dan tidak tersimpan
    - **Property 37: Pencatatan Metode dan Timestamp Selalu Lengkap** — record dengan status COLLECTED selalu memiliki `method` dan `collected_at` tidak null
    - **Property 38: Timeout Chat Menghasilkan Status Unavailable** — affiliate yang tidak membalas dalam 48 jam menghasilkan status `unavailable` dengan `phone_number` null
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 11.7, 11.9, 11.10**

  - [x] 7.3 Tulis unit test untuk WhatsAppCollectorAgent
    - Test edge case: bio kosong, bio dengan beberapa nomor, nomor dengan format tidak standar, timeout tepat di batas 48 jam
    - _Requirements: 11.3, 11.6, 11.9_

- [x] 8. Checkpoint — Pastikan semua test lulus
  - Pastikan semua test lulus, tanyakan kepada pengguna jika ada pertanyaan.

- [x] 9. Implementasi Sender Agent
  - [x] 9.1 Implementasi `SenderAgent` di `app/agents/sender_agent.py`
    - Implementasi `send_single_invitation()`: kirim via WhatsApp API menggunakan nomor dari `WhatsAppCollectionRecord`, catat status + timestamp
    - Implementasi `send_bulk_invitations()`: iterasi daftar influencer dengan rate limiting ≤ 100 undangan/menit menggunakan token bucket atau sliding window
    - Implementasi substitusi variabel template: ganti semua `{{variable}}` dengan data influencer, validasi tidak ada placeholder tersisa
    - Implementasi guard blacklist: tolak pengiriman ke influencer blacklisted dengan `BlacklistViolationError`
    - Implementasi penjadwalan: jika `scheduled_at` diisi, simpan undangan dengan status `SCHEDULED` dan proses pada waktu yang ditentukan
    - Implementasi `generate_invitation_report()`: hitung total berhasil, gagal, tertunda
    - Publish event ke Redis Streams setelah setiap pengiriman
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 8.3, 11.8_

  - [x] 9.2 Tulis property test untuk SenderAgent
    - **Property 7: Semua Influencer Terpilih Menerima Undangan** — setiap influencer dalam daftar memiliki record undangan SENT atau FAILED
    - **Property 8: Rate Limiting Undangan** — jumlah undangan dalam window 60 detik manapun tidak melebihi 100
    - **Property 9: Pencatatan Status Pengiriman Lengkap** — total SENT + FAILED + PENDING = total influencer diproses
    - **Property 10: Kegagalan Satu Tidak Menghentikan Proses** — influencer gagal dicatat FAILED, proses lanjut ke berikutnya
    - **Property 11: Substitusi Variabel Template Lengkap** — pesan yang dihasilkan tidak mengandung `{{...}}` yang belum disubstitusi
    - **Property 27: Pengiriman Menolak Influencer Blacklist** — pengiriman ke influencer blacklisted selalu ditolak
    - **Property 39: Nomor Tersimpan Digunakan oleh Sender** — nomor tujuan pengiriman sama dengan `phone_number` di `WhatsAppCollectionRecord`
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 8.3, 11.8**

  - [x] 9.3 Tulis unit test untuk SenderAgent
    - Test edge case: daftar influencer kosong, semua pengiriman gagal, pengiriman terjadwal
    - _Requirements: 3.4, 3.7_

- [x] 10. Implementasi Monitor Agent
  - [x] 10.1 Implementasi `MonitorAgent` di `app/agents/monitor_agent.py`
    - Implementasi `start_monitoring()` dan `stop_monitoring()`: kelola background task periodik setiap 30 menit
    - Implementasi `check_new_content()`: ambil video baru via `TikTokAPIClient`, ekstrak metrik (views, likes, comments, shares — tidak boleh null atau negatif)
    - Implementasi `validate_affiliate_link()`: deteksi tautan afiliasi valid sesuai kampanye (deterministik)
    - Implementasi notifikasi ke manajer jika konten tidak memenuhi panduan dalam 1 jam setelah terdeteksi
    - Implementasi penyimpanan riwayat metrik harian ke PostgreSQL
    - Implementasi `generate_final_report()`: agregasi total tayangan, GMV, tingkat konversi per influencer
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 10.2 Tulis property test untuk MonitorAgent
    - **Property 12: Metrik Konten Lengkap** — semua metrik (views, likes, comments, shares) tidak null dan tidak negatif
    - **Property 13: Deteksi Tautan Afiliasi Konsisten** — fungsi deteksi mengembalikan True jika dan hanya jika tautan valid ada
    - **Property 14: Riwayat Metrik Tersimpan Per Hari** — mengambil riwayat untuk tanggal tertentu mengembalikan semua metrik pada tanggal tersebut
    - **Property 15: Laporan Akhir Mencakup Semua Influencer** — laporan akhir mengandung data untuk setiap influencer yang berpartisipasi
    - **Validates: Requirements 4.2, 4.3, 4.5, 4.6**

  - [x] 10.3 Tulis unit test untuk MonitorAgent
    - Test edge case: kampanye tanpa konten, konten tanpa tautan afiliasi, metrik dengan nilai nol
    - _Requirements: 4.4, 4.5_

- [x] 11. Implementasi Classifier Agent
  - [x] 11.1 Implementasi `ClassifierAgent` di `app/agents/classifier_agent.py`
    - Implementasi `classify_feedback()`: klasifikasikan umpan balik ke salah satu dari empat `FeedbackCategory` menggunakan NLP client
    - Implementasi routing ke manual review: set `requires_manual_review = True` jika kategori `NEEDS_MORE_INFO` ATAU `confidence_score < 0.8`
    - Implementasi auto-update status influencer menjadi `REJECTED` jika klasifikasi `Menolak`
    - Implementasi `get_classification_summary()`: hitung distribusi per kategori, total harus sama dengan total umpan balik
    - Publish event ke Redis Streams setelah klasifikasi
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 11.2 Tulis property test untuk ClassifierAgent
    - **Property 16: Klasifikasi Menghasilkan Kategori Valid** — hasil klasifikasi selalu salah satu dari empat kategori valid
    - **Property 17: Routing ke Manual Review** — `requires_manual_review = True` jika `NEEDS_MORE_INFO` atau `confidence_score < 0.8`
    - **Property 18: Konsistensi Ringkasan Klasifikasi** — total semua kategori dalam ringkasan = total umpan balik yang diklasifikasikan
    - **Property 19: Update Status Influencer Setelah Penolakan** — status influencer diperbarui menjadi REJECTED setelah klasifikasi Menolak
    - **Validates: Requirements 5.1, 5.3, 5.4, 5.5, 5.6**

  - [x] 11.3 Tulis unit test untuk ClassifierAgent
    - Test edge case: umpan balik kosong, umpan balik ambigu, confidence tepat di batas 0.8
    - _Requirements: 5.2, 5.4_

- [x] 12. Checkpoint — Pastikan semua test lulus
  - Pastikan semua test lulus, tanyakan kepada pengguna jika ada pertanyaan.

- [x] 13. Implementasi Agent Orchestrator dan Campaign Service
  - [x] 13.1 Implementasi `AgentOrchestrator` di `app/agents/orchestrator.py`
    - Implementasi `start_campaign()`: orkestrasi urutan SelectorAgent → SenderAgent → MonitorAgent, subscribe ke Redis Streams untuk event antar agen
    - Implementasi `stop_campaign()`: hentikan semua agen yang berjalan untuk kampanye tersebut
    - Implementasi `get_campaign_status()`: kembalikan status terkini dari semua agen
    - Implementasi `handle_agent_event()`: proses event dari Redis Streams (feedback_received → ClassifierAgent)
    - _Requirements: 2.4, 3.1, 4.1, 5.1_

  - [x] 13.2 Implementasi `CampaignService` di `app/services/campaign_service.py`
    - Implementasi CRUD kampanye: `create()`, `get()`, `update()`, `delete()`
    - Implementasi `start_campaign()` dan `stop_campaign()` yang mendelegasikan ke `AgentOrchestrator`
    - Implementasi sinkronisasi data Affiliate Center setiap 15 menit via background task
    - _Requirements: 1.3, 6.1_

- [x] 14. Implementasi Report Service dan Dashboard
  - [x] 14.1 Implementasi `ReportService` di `app/services/report_service.py`
    - Implementasi `generate_campaign_report()`: agregasi total influencer, tingkat penerimaan, total tayangan, total GMV, biaya per konversi
    - Implementasi filter laporan berdasarkan rentang tanggal, kategori influencer, status kampanye
    - Implementasi ekspor ke CSV, Excel (openpyxl), dan PDF (reportlab atau weasyprint)
    - Pastikan laporan dihasilkan dalam waktu ≤ 30 detik untuk data hingga 12 bulan (gunakan query yang dioptimasi dengan indeks)
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 14.2 Tulis property test untuk ReportService
    - **Property 32: Kelengkapan Laporan Performa** — laporan selalu mengandung semua metrik yang diperlukan (total influencer, tingkat penerimaan, tayangan, GMV, biaya per konversi)
    - **Property 33: Filter Laporan Konsisten** — semua data dalam laporan yang difilter memenuhi semua kriteria filter yang diterapkan
    - **Validates: Requirements 10.1, 10.3**

  - [x] 14.3 Implementasi notifikasi threshold di `app/services/notification_service.py`
    - Implementasi `check_and_notify()`: bandingkan metrik kampanye dengan `alert_thresholds` di `CampaignSettings`, generate notifikasi jika terlampaui
    - _Requirements: 6.4_

  - [x] 14.4 Tulis property test untuk NotificationService
    - **Property 20: Notifikasi Threshold Metrik** — setiap metrik yang melampaui ambang batas menghasilkan notifikasi dengan informasi metrik dan nilai ambang batas
    - **Validates: Requirements 6.4**

- [x] 15. Implementasi REST API Gateway
  - [x] 15.1 Implementasi router kampanye di `app/api/campaigns.py`
    - Implementasi endpoint: `POST /campaigns`, `GET /campaigns/{id}`, `POST /campaigns/{id}/start`, `POST /campaigns/{id}/stop`, `GET /campaigns/{id}/status`, `GET /campaigns/{id}/report`
    - Terapkan dependency injection untuk autentikasi JWT dan RBAC
    - Pastikan `GET /campaigns/{id}/status` merespons dalam ≤ 3 detik (gunakan Redis cache)
    - _Requirements: 6.1, 6.2_

  - [x] 15.2 Implementasi router influencer dan blacklist di `app/api/influencers.py`
    - Implementasi endpoint: `POST /influencers/select`, `GET /influencers/blacklist`, `POST /influencers/blacklist`, `DELETE /influencers/blacklist/{id}`
    - _Requirements: 2.1, 8.1, 8.4_

  - [x] 15.3 Implementasi router template di `app/api/templates.py`
    - Implementasi endpoint: `POST /templates`, `GET /templates`, `PUT /templates/{id}`, `DELETE /templates/{id}`
    - _Requirements: 7.1, 7.3_

  - [x] 15.4 Implementasi router laporan dan auth di `app/api/reports.py` dan `app/api/auth.py`
    - Implementasi endpoint laporan: `GET /reports/campaigns`, `POST /reports/export`
    - Implementasi endpoint auth: `POST /auth/login`, `POST /auth/logout`, `POST /auth/refresh`
    - _Requirements: 9.1, 10.1, 10.4_

  - [x] 15.5 Implementasi ekspor data kampanye di endpoint `POST /reports/export`
    - Dukung format CSV dan Excel sesuai data yang ditampilkan di sistem
    - _Requirements: 6.5_

  - [x] 15.6 Tulis property test untuk ekspor data
    - **Property 21: Ekspor Data Lengkap** — file CSV/Excel yang dihasilkan mengandung semua baris dan kolom sesuai data di sistem
    - **Validates: Requirements 6.5**

- [x] 16. Implementasi Dashboard Pencarian dan Detail Affiliate (Requirement 12)
  - [x] 16.1 Implementasi router affiliate search di `app/api/affiliates.py`
    - Implementasi `GET /api/v1/affiliates/search` dengan query params: `min_followers`, `max_followers`, `min_engagement_rate`, `categories`, `locations`, `page`, `page_size`
    - Implementasi `GET /api/v1/affiliates/{id}` yang mengembalikan `AffiliateDetail` lengkap termasuk `contact_channel`
    - Implementasi `POST /api/v1/affiliates/{id}/contact`: jika `phone_number` tersimpan → kirim via WhatsApp API; jika tidak → trigger `WhatsAppCollectorAgent.collect_whatsapp_number()`
    - Terapkan dependency injection untuk autentikasi JWT
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [x] 16.2 Implementasi logika pemilihan kanal kontak di `app/services/contact_service.py`
    - Implementasi `get_contact_channel(affiliate_id)`: kembalikan `"whatsapp"` jika `phone_number` ada di DB, `"seller_center_chat"` jika tidak
    - Implementasi `send_contact_message(affiliate_id, message)`: delegasikan ke WhatsApp API atau trigger `WhatsAppCollectorAgent` sesuai kanal
    - _Requirements: 12.4, 12.5_

  - [x] 16.3 Tulis property test untuk Affiliate Search
    - **Property 40: Hasil Pencarian Affiliate Memenuhi Semua Kriteria** — setiap affiliate dalam hasil memenuhi semua kriteria yang diterapkan
    - **Property 41: Detail Affiliate Mengandung Semua Field** — response detail selalu mengandung semua field wajib
    - **Property 42: Pemilihan Kanal Kontak Berdasarkan Ketersediaan Nomor WA** — contact_channel selalu konsisten dengan keberadaan phone_number
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5**

- [x] 17. Implementasi Learning Engine (Requirement 13)
  - [x] 17.1 Implementasi `LearningEngine` di `app/agents/learning_engine.py`
    - Implementasi `record_campaign_outcome(campaign_id)`: ambil data performa kampanye (GMV, conversion_rate, acceptance_rate per influencer) dan simpan sebagai `CampaignOutcome`
    - Implementasi `retrain_selection_model()`: latih ulang model menggunakan semua `CampaignOutcome`, influencer dengan GMV dan conversion_rate tinggi mendapat bobot lebih tinggi; simpan `ModelVersion` baru; jalankan sebagai background task
    - Implementasi `retrain_classifier_model()`: latih ulang model klasifikasi menggunakan data umpan balik yang telah diklasifikasikan (termasuk hasil tinjauan manual); simpan `ModelVersion` baru; jalankan sebagai background task
    - Implementasi `get_influencer_recommendations(criteria, top_n)`: gunakan model seleksi terkini untuk menghasilkan `InfluencerRecommendation` dengan `confidence_score` dalam [0.0, 1.0]
    - Implementasi `get_model_performance_history()`: kembalikan semua `ModelVersion` diurutkan dari terbaru
    - Pastikan `version` pada `ModelVersion` bertambah monoton per `model_type`
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [x] 17.2 Integrasikan `LearningEngine` ke `AgentOrchestrator`
    - Panggil `LearningEngine.record_campaign_outcome()` secara otomatis saat kampanye berpindah ke status `COMPLETED`
    - Jadwalkan `retrain_selection_model()` dan `retrain_classifier_model()` sebagai background task setelah `record_campaign_outcome()` selesai
    - Pastikan retraining tidak memblokir atau mengubah state kampanye yang sedang `ACTIVE`
    - _Requirements: 13.2, 13.5_

  - [x] 17.3 Tulis property test untuk LearningEngine
    - **Property 43: Versi Model Bertambah Monoton** — setiap retraining menghasilkan `version` yang lebih besar dari versi sebelumnya untuk `model_type` yang sama
    - **Property 44: Retraining Menghasilkan ModelVersion Lengkap** — setiap `ModelVersion` yang dikembalikan memiliki semua field wajib tidak null
    - **Property 45: Confidence Score Rekomendasi dalam Rentang Valid** — semua `confidence_score` dan `predicted_conversion_rate` dalam [0.0, 1.0]
    - **Property 46: Retraining Tidak Mengubah State Kampanye Aktif** — state kampanye ACTIVE tidak berubah selama retraining berlangsung
    - **Validates: Requirements 13.1, 13.2, 13.4, 13.5, 13.6**

  - [x] 17.4 Tulis unit test untuk LearningEngine
    - Test edge case: tidak ada data outcome (retraining dilewati), kampanye dengan semua influencer menolak, retraining gagal di tengah jalan
    - _Requirements: 13.2, 13.5_

- [x] 18. Wiring dan integrasi akhir
    - Daftarkan semua router API dengan prefix `/api/v1`
    - Setup middleware: CORS, JWT authentication, audit logging
    - Setup startup/shutdown event: inisialisasi koneksi database, Redis, background tasks (monitoring periodik, sinkronisasi Affiliate Center)
    - _Requirements: 1.1, 4.1, 9.4_

  - [x] 16.2 Integrasikan Redis Streams sebagai message queue antar agen
    - Buat `app/queue/streams.py` dengan helper publish/consume untuk Redis Streams
    - Pastikan setiap agen memiliki consumer group sendiri
    - _Requirements: 3.1, 4.1, 5.1_

  - [x] 16.3 Tulis integration test untuk alur end-to-end
    - Test alur lengkap: seleksi influencer → pengumpulan nomor WA → pengiriman undangan → klasifikasi umpan balik
    - Test integrasi Affiliate Center, TikTok API, WhatsApp API dengan mock server
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 11.1_

- [x] 19. Checkpoint akhir — Pastikan semua test lulus
  - Pastikan semua test lulus dan coverage unit test minimal 80%. Tanyakan kepada pengguna jika ada pertanyaan.

---

## Catatan

- Task bertanda `*` bersifat opsional dan dapat dilewati untuk MVP yang lebih cepat
- Setiap task mereferensikan requirements spesifik untuk keterlacakan
- Property test memvalidasi properti kebenaran universal menggunakan `hypothesis`
- Unit test memvalidasi contoh spesifik dan edge case menggunakan `pytest`
- Checkpoint memastikan validasi inkremental di setiap fase
