"""Seed data untuk message_history."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from app.database import AsyncSessionFactory

MESSAGES = [
    # Sari Cantika (Skincare) — inf-001
    {
        "affiliate_id": "inf-001",
        "affiliate_name": "Sari Cantika",
        "wa_category": "Skincare",
        "to_number": "+6281234567890",
        "thread": [
            ("outbound", "Halo Sari! Kami dari MCN ingin mengundang kamu untuk kampanye produk skincare terbaru kami. Apakah kamu tertarik?", -5),
            ("inbound", "Halo! Wah menarik sekali, boleh ceritakan lebih lanjut?", -4),
            ("outbound", "Tentu! Produknya adalah serum vitamin C dari brand lokal premium. Komisi 15% per penjualan. Tertarik?", -3),
            ("inbound", "Sounds good! Kapan mulainya?", -2),
            ("outbound", "Kampanye mulai minggu depan. Kami akan kirim brief lengkap segera ya!", -1),
        ]
    },
    # Budi Santoso (FnB) — inf-002
    {
        "affiliate_id": "inf-002",
        "affiliate_name": "Budi Santoso",
        "wa_category": "FnB",
        "to_number": "+6281234567891",
        "thread": [
            ("outbound", "Halo Budi! Ada kampanye produk minuman kesehatan yang cocok untuk konten kamu. Mau tau detailnya?", -10),
            ("inbound", "Boleh, kirim detailnya dong!", -9),
            ("outbound", "Ini brief-nya: Produk minuman herbal, target 5 video per bulan, komisi 12%. Gimana?", -8),
            ("inbound", "Oke saya tertarik. Produknya bisa dikirim ke alamat saya?", -7),
            ("outbound", "Bisa! Tolong konfirmasi alamat pengiriman ya Budi.", -6),
            ("inbound", "Jl. Sudirman No. 45, Jakarta Selatan. Terima kasih!", -5),
        ]
    },
    # Dewi Rahayu (Fashion) — inf-003
    {
        "affiliate_id": "inf-003",
        "affiliate_name": "Dewi Rahayu",
        "wa_category": "Fashion",
        "to_number": "+6281234567892",
        "thread": [
            ("outbound", "Hi Dewi! Kami punya koleksi fashion terbaru yang perfect untuk konten kamu. Tertarik kolaborasi?", -15),
            ("inbound", "Hii! Wah boleh banget, brand apa?", -14),
            ("outbound", "Brand lokal premium — Batik Modern. Mereka lagi launch koleksi batik kontemporer.", -13),
            ("inbound", "Ooh suka banget sama batik modern! Komisinya berapa?", -12),
            ("outbound", "Komisi 18% + free produk senilai 500rb. Deal?", -11),
            ("inbound", "Deal! Kapan bisa mulai?", -10),
        ]
    },
    # Lestari Wulan (Skincare) — inf-009
    {
        "affiliate_id": "inf-009",
        "affiliate_name": "Lestari Wulan",
        "wa_category": "Skincare",
        "to_number": "+6281234567898",
        "thread": [
            ("outbound", "Halo Lestari! Ada penawaran kolaborasi untuk produk sunscreen SPF 50+. Minat?", -3),
            ("inbound", "Halo! Boleh, produknya sudah BPOM?", -2),
            ("outbound", "Sudah BPOM dan dermatologically tested. Kami bisa kirim sample dulu kalau mau.", -1),
        ]
    },
    # Rina Kusuma (Olahraga) — inf-005
    {
        "affiliate_id": "inf-005",
        "affiliate_name": "Rina Kusuma",
        "wa_category": "Olahraga",
        "to_number": "+6281234567894",
        "thread": [
            ("outbound", "Hi Rina! Kami punya brand suplemen olahraga yang cocok banget sama konten fitness kamu!", -20),
            ("inbound", "Wah menarik! Produknya apa aja?", -19),
            ("outbound", "Protein shake, BCAA, dan pre-workout. Semua sudah BPOM. Komisi 20%.", -18),
            ("inbound", "Bagus! Tapi saya perlu coba dulu sebelum promote.", -17),
            ("outbound", "Tentu! Kami kirim sample pack gratis. Alamat pengirimannya?", -16),
        ]
    },
]

async def seed():
    async with AsyncSessionFactory() as db:
        # Ambil WA number IDs
        r = await db.execute(text("SELECT id, category FROM whatsapp_numbers"))
        wa_map = {row["category"]: str(row["id"]) for row in r.mappings().all()}

        # Ambil from_number per kategori
        r2 = await db.execute(text("SELECT category, phone_number FROM whatsapp_numbers"))
        phone_map = {row["category"]: row["phone_number"] for row in r2.mappings().all()}

        count = 0
        now = datetime.now(timezone.utc)

        for conv in MESSAGES:
            wa_number_id = wa_map.get(conv["wa_category"])
            from_number = phone_map.get(conv["wa_category"])

            for i, (direction, content, hours_ago) in enumerate(conv["thread"]):
                sent_at = now + timedelta(hours=hours_ago, minutes=i * 5)
                msg_id = str(uuid.uuid4())

                await db.execute(text("""
                    INSERT INTO message_history
                        (id, affiliate_id, affiliate_name, direction, message_content,
                         wa_number_id, from_number, to_number, status, sent_at)
                    VALUES
                        (:id, :affiliate_id, :affiliate_name, :direction, :content,
                         :wa_number_id, :from_number, :to_number, 'read', :sent_at)
                    ON CONFLICT (id) DO NOTHING
                """), {
                    "id": msg_id,
                    "affiliate_id": conv["affiliate_id"],
                    "affiliate_name": conv["affiliate_name"],
                    "direction": direction,
                    "content": content,
                    "wa_number_id": wa_number_id,
                    "from_number": from_number if direction == "outbound" else conv["to_number"],
                    "to_number": conv["to_number"] if direction == "outbound" else from_number,
                    "sent_at": sent_at,
                })
                count += 1

        await db.commit()
        print(f"Seeded {count} messages untuk {len(MESSAGES)} percakapan.")

asyncio.run(seed())
