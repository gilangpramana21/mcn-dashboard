"""Seed variasi pesan yang natural untuk message learning."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://mcn_user:mcn_password@localhost/mcn_dashboard")

# Variasi pesan yang natural, tidak terlihat seperti template
VARIATIONS = [
    # Casual & friendly
    "Halo {name}! 👋\n\nLagi scroll dan nemu konten kamu — keren banget sih!\n\nKami dari tim MCN lagi nyari kreator untuk kolaborasi produk yang kayaknya cocok sama niche kamu. Boleh minta nomor WA-nya buat ngobrol lebih lanjut? 😊",

    # Direct & simple
    "Hai {name}!\n\nKonten kamu bagus, kami tertarik untuk kolaborasi. Ada waktu ngobrol sebentar? Boleh minta nomor WA-nya? 🙏",

    # Warm & personal
    "Halo {name} 😊\n\nSuka banget sama konten kamu! Kami dari MCN pengen ajak kolaborasi nih. Boleh share nomor WA buat diskusi lebih lanjut?",

    # Professional tapi santai
    "Hi {name}!\n\nKami dari tim MCN — tertarik banget sama konten kamu dan pengen explore kemungkinan kolaborasi bareng.\n\nBoleh minta nomor WA-nya? Mau ngobrol santai dulu 😄",

    # Short & punchy
    "Halo {name}! Konten kamu keren 🔥 Kami dari MCN mau ajak kolaborasi. Boleh minta WA-nya?",

    # Story-based
    "Hai {name}!\n\nTim kami lagi nyari kreator TikTok yang genuine dan kamu masuk list kami 😄\n\nBoleh kenalan dulu? Share nomor WA-nya ya, mau cerita lebih detail soal kolaborasinya!",

    # Question-based
    "Halo {name}! 👋\n\nPernah kepikiran kolaborasi sama brand? Kami dari MCN punya beberapa produk yang kayaknya cocok sama audience kamu.\n\nBoleh minta nomor WA buat diskusi? Santai aja kok 😊",

    # Compliment-first
    "Hai {name}!\n\nEngagement rate kamu bagus banget — artinya audience kamu beneran engaged sama konten kamu 👏\n\nKami dari MCN mau ajak kolaborasi. Boleh share nomor WA-nya?",
]

async def seed():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Cek template ada
        result = await db.execute(text("""
            SELECT id FROM message_templates
            WHERE message_type = 'request_whatsapp' AND is_active = TRUE
            LIMIT 1
        """))
        row = result.mappings().first()

        if not row:
            # Buat template dulu
            await db.execute(text("""
                INSERT INTO message_templates (id, name, message_type, content, is_active)
                VALUES (gen_random_uuid(), 'WA Request Default', 'request_whatsapp',
                        'Halo {name}! Kami dari MCN tertarik kolaborasi. Boleh minta WA-nya?',
                        TRUE)
                ON CONFLICT DO NOTHING
            """))
            await db.commit()
            result = await db.execute(text("""
                SELECT id FROM message_templates
                WHERE message_type = 'request_whatsapp' AND is_active = TRUE
                LIMIT 1
            """))
            row = result.mappings().first()

        template_id = str(row["id"])
        print(f"Template ID: {template_id}")

        # Cek sudah ada variasi
        existing = await db.execute(text("""
            SELECT COUNT(*) as cnt FROM message_variations WHERE template_id = :tid
        """), {"tid": template_id})
        count = existing.scalar()

        if count and count > 0:
            print(f"Sudah ada {count} variasi, skip seed.")
            return

        # Insert variasi
        for i, content in enumerate(VARIATIONS):
            await db.execute(text("""
                INSERT INTO message_variations (template_id, content, is_active)
                VALUES (:tid, :content, TRUE)
            """), {"tid": template_id, "content": content})
            print(f"Added variation {i+1}: {content[:50]}...")

        await db.commit()
        print(f"\n✅ Berhasil seed {len(VARIATIONS)} variasi pesan!")

if __name__ == "__main__":
    asyncio.run(seed())
