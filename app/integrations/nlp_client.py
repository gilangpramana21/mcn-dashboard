"""NLP Client — klasifikasi feedback menggunakan TF-IDF + cosine similarity.

Pendekatan: zero-shot classification berbasis kemiripan teks dengan scikit-learn.
Tidak butuh PyTorch, tidak butuh GPU, ringan dan stabil di semua platform.
Fallback ke keyword matching jika scikit-learn tidak tersedia.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Tuple

from app.models.domain import FeedbackCategory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Contoh kalimat per kategori (training data sederhana)
# ---------------------------------------------------------------------------

_EXAMPLES: List[Tuple[str, FeedbackCategory]] = [
    # ACCEPTED
    ("iya saya mau bergabung", FeedbackCategory.ACCEPTED),
    ("ok siap kak", FeedbackCategory.ACCEPTED),
    ("setuju deal", FeedbackCategory.ACCEPTED),
    ("bisa kak saya tertarik", FeedbackCategory.ACCEPTED),
    ("gas lah kapan mulai", FeedbackCategory.ACCEPTED),
    ("oke saya bersedia", FeedbackCategory.ACCEPTED),
    ("mau dong boleh", FeedbackCategory.ACCEPTED),
    ("siap bergabung kampanye", FeedbackCategory.ACCEPTED),
    ("yes deal confirmed", FeedbackCategory.ACCEPTED),
    ("acc lanjut aja", FeedbackCategory.ACCEPTED),
    ("sip mantap ayo", FeedbackCategory.ACCEPTED),
    ("boleh kak saya mau coba", FeedbackCategory.ACCEPTED),
    # REJECTED
    ("maaf tidak bisa", FeedbackCategory.REJECTED),
    ("tidak tertarik kak", FeedbackCategory.REJECTED),
    ("gak mau skip", FeedbackCategory.REJECTED),
    ("nggak bisa lagi banyak kerjaan", FeedbackCategory.REJECTED),
    ("sorry tidak berminat", FeedbackCategory.REJECTED),
    ("decline tidak cocok", FeedbackCategory.REJECTED),
    ("ga bisa lewat dulu", FeedbackCategory.REJECTED),
    ("tidak sesuai dengan konten saya", FeedbackCategory.REJECTED),
    ("maaf lagi sibuk", FeedbackCategory.REJECTED),
    ("no thanks tidak mau", FeedbackCategory.REJECTED),
    # NEEDS_MORE_INFO
    ("komisinya berapa persen", FeedbackCategory.NEEDS_MORE_INFO),
    ("syarat dan ketentuannya gimana", FeedbackCategory.NEEDS_MORE_INFO),
    ("produk apa yang dipromosikan", FeedbackCategory.NEEDS_MORE_INFO),
    ("berapa budget kampanye ini", FeedbackCategory.NEEDS_MORE_INFO),
    ("bisa jelaskan lebih detail", FeedbackCategory.NEEDS_MORE_INFO),
    ("kapan deadline kontennya", FeedbackCategory.NEEDS_MORE_INFO),
    ("fee nya berapa kak", FeedbackCategory.NEEDS_MORE_INFO),
    ("kontraknya seperti apa", FeedbackCategory.NEEDS_MORE_INFO),
    ("info lebih lanjut dong", FeedbackCategory.NEEDS_MORE_INFO),
    ("brand apa ini", FeedbackCategory.NEEDS_MORE_INFO),
    # NO_RESPONSE
    ("ok", FeedbackCategory.NO_RESPONSE),
    ("hmm", FeedbackCategory.NO_RESPONSE),
    ("noted", FeedbackCategory.NO_RESPONSE),
]

# ---------------------------------------------------------------------------
# Keyword fallback
# ---------------------------------------------------------------------------

_KEYWORDS_ACCEPTED = [
    "iya", "ok", "setuju", "mau", "bisa", "siap", "yes", "deal", "oke",
    "menerima", "bergabung", "tertarik", "saya mau", "saya bisa", "boleh",
    "lanjut", "acc", "approved", "confirm", "konfirmasi", "gas", "mantap",
    "sip", "ayo", "yuk", "bersedia",
]

_KEYWORDS_REJECTED = [
    "tidak bisa", "tidak mau", "maaf tidak", "tidak tertarik",
    "tidak", "nggak", "gak", "no", "tolak", "menolak", "decline",
    "maaf", "sorry", "tidak berminat", "skip", "pass", "gausah",
    "ga bisa", "ga mau", "gak mau", "gak bisa", "belum bisa",
]

_KEYWORDS_NEEDS_MORE_INFO = [
    "berapa", "bagaimana", "apa", "kapan", "dimana", "info", "detail",
    "jelaskan", "tanya", "?", "gimana", "seperti apa", "ketentuan",
    "syarat", "benefit", "komisi", "fee", "bayaran", "rate", "harga",
    "budget", "kontrak", "durasi", "produk apa", "brand apa",
]


@dataclass
class NLPResult:
    category: FeedbackCategory
    confidence_score: float
    reasoning: str
    used_ai: bool


@lru_cache(maxsize=1)
def _load_classifier():
    """Build TF-IDF classifier dari contoh kalimat."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        texts = [t for t, _ in _EXAMPLES]
        labels = [c for _, c in _EXAMPLES]

        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 4),
            min_df=1,
        )
        X = vectorizer.fit_transform(texts)
        logger.info("TF-IDF NLP classifier berhasil dimuat (%d contoh).", len(texts))
        return vectorizer, X, labels
    except Exception as exc:
        logger.warning("Gagal memuat TF-IDF classifier: %s", exc)
        return None


class NLPClassifierClient:
    """Klasifikasi feedback menggunakan TF-IDF cosine similarity."""

    async def classify(self, text: str) -> NLPResult:
        if not text or not text.strip():
            return NLPResult(
                category=FeedbackCategory.NO_RESPONSE,
                confidence_score=1.0,
                reasoning="Pesan kosong",
                used_ai=False,
            )

        clf = _load_classifier()
        if clf is not None:
            try:
                return self._classify_with_tfidf(clf, text)
            except Exception as exc:
                logger.warning("TF-IDF gagal, fallback ke keyword: %s", exc)

        return self._classify_with_keywords(text)

    def _classify_with_tfidf(self, clf, text: str) -> NLPResult:
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        # Keyword check dulu sebagai override untuk kasus yang jelas
        text_lower = text.lower()
        
        # Strong accepted signals — tambahkan "ok deal" dan variasi
        strong_accepted = ["iya", "setuju", "siap bergabung", "saya mau", "saya bisa",
                          "ok deal", "oke deal", "deal", "acc", "confirm", "bersedia",
                          "gas lah", "ayo", "yuk", "boleh kak"]
        for kw in strong_accepted:
            if kw in text_lower:
                return NLPResult(
                    category=FeedbackCategory.ACCEPTED,
                    confidence_score=0.9,
                    reasoning=f"Strong accepted keyword: '{kw}'",
                    used_ai=False,
                )

        # Strong rejected signals
        strong_rejected = ["tidak bisa", "tidak mau", "tidak tertarik", "tidak berminat",
                          "nggak mau", "gak mau", "ga mau", "no thanks", "tolak", "menolak",
                          "decline", "skip", "maaf tidak", "sorry tidak"]
        for kw in strong_rejected:
            if kw in text_lower:
                return NLPResult(
                    category=FeedbackCategory.REJECTED,
                    confidence_score=0.9,
                    reasoning=f"Strong keyword match: '{kw}'",
                    used_ai=False,
                )
        
        # Strong needs_more_info signals
        strong_needs_info = ["berapa", "bagaimana", "gimana", "?", "info lebih", "jelaskan",
                            "fee", "komisi", "syarat", "ketentuan", "kontrak"]
        needs_info_count = sum(1 for kw in strong_needs_info if kw in text_lower)
        if needs_info_count >= 1 and not any(kw in text_lower for kw in ["iya", "ok", "setuju", "mau", "siap"]):
            return NLPResult(
                category=FeedbackCategory.NEEDS_MORE_INFO,
                confidence_score=0.85,
                reasoning=f"Needs info keyword match: {needs_info_count} keywords",
                used_ai=False,
            )

        vectorizer, X_train, labels = clf
        text_clean = re.sub(r'[^\w\s?]', ' ', text.lower())
        X_query = vectorizer.transform([text_clean])
        similarities = cosine_similarity(X_query, X_train)[0]

        # Agregasi skor per kategori
        category_scores: dict = {}
        for i, label in enumerate(labels):
            if label not in category_scores:
                category_scores[label] = []
            category_scores[label].append(similarities[i])

        # Ambil max similarity per kategori
        best_category = max(category_scores, key=lambda c: max(category_scores[c]))
        best_score = float(max(category_scores[best_category]))

        # Normalize confidence
        total = sum(max(v) for v in category_scores.values())
        confidence = best_score / total if total > 0 else 0.0
        confidence = min(1.0, max(0.0, confidence))

        return NLPResult(
            category=best_category,
            confidence_score=confidence,
            reasoning=f"TF-IDF similarity: {best_score:.3f} → {best_category.value}",
            used_ai=True,
        )

    def _classify_with_keywords(self, text: str) -> NLPResult:
        text_clean = re.sub(r'[^\w\s?]', ' ', text.lower())

        rejected_matches = sum(1 for kw in _KEYWORDS_REJECTED if kw in text_clean)
        accepted_matches = sum(1 for kw in _KEYWORDS_ACCEPTED if kw in text_clean)
        needs_info_matches = sum(1 for kw in _KEYWORDS_NEEDS_MORE_INFO if kw in text_clean)

        scores = {
            FeedbackCategory.ACCEPTED: (accepted_matches, len(_KEYWORDS_ACCEPTED)),
            FeedbackCategory.REJECTED: (rejected_matches, len(_KEYWORDS_REJECTED)),
            FeedbackCategory.NEEDS_MORE_INFO: (needs_info_matches, len(_KEYWORDS_NEEDS_MORE_INFO)),
        }

        best_category = max(scores, key=lambda c: scores[c][0])
        best_matches, best_total = scores[best_category]

        if best_matches == 0:
            return NLPResult(
                category=FeedbackCategory.NO_RESPONSE,
                confidence_score=0.3,
                reasoning="Tidak ada keyword yang cocok",
                used_ai=False,
            )

        confidence = min(0.75, best_matches / best_total)
        return NLPResult(
            category=best_category,
            confidence_score=confidence,
            reasoning=f"Keyword: {best_matches} kata cocok → {best_category.value}",
            used_ai=False,
        )
