"""Test NLP Classifier — jalankan: venv/bin/python test_nlp.py"""
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import asyncio
from app.integrations.nlp_client import NLPClassifierClient

TEST_CASES = [
    ("gas lah kak, kapan mulainya?", "Menerima"),
    ("oke siap, saya mau bergabung", "Menerima"),
    ("maaf lagi banyak kerjaan, gak bisa", "Menolak"),
    ("tidak tertarik kak", "Menolak"),
    ("komisinya berapa persen kak?", "Butuh Info"),
    ("syarat dan ketentuannya gimana?", "Butuh Info"),
    ("ok", "Menerima"),
    ("", "Tidak Respons"),
]

async def main():
    client = NLPClassifierClient()
    print("=" * 60)
    print("TEST NLP CLASSIFIER")
    print("=" * 60)

    for text, expected in TEST_CASES:
        result = await client.classify(text)
        status = "✓" if expected.lower() in result.category.value.lower() else "✗"
        ai_label = "AI" if result.used_ai else "Keyword"
        display = f"'{text[:40]}...'" if len(text) > 40 else f"'{text}'"
        print(f"{status} [{ai_label}] {display}")
        print(f"   → {result.category.value} (confidence: {result.confidence_score:.2%})")
        print(f"   → {result.reasoning}")
        print()

asyncio.run(main())
