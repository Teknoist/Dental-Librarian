from __future__ import annotations

from urllib.parse import urlparse

from src.ai.local_ai_client import LocalAIClient
from src.core.config import Config
from src.core.models import Candidate

BRANDS = [
    "osstem", "straumann", "nobel", "megagen", "dentsply", "medentika", "biohorizons",
    "zimmer", "mis", "neodent", "camlog", "bego", "bredent", "icx", "ankylos",
]
KEYWORDS = ["implant", "exocad", "cadcam", "library", "implantlibrary", "stl", "xml", "dme"]


class CandidateClassifier:
    def __init__(self, config: Config, ai_client: LocalAIClient | None = None) -> None:
        self.config = config
        self.ai_client = ai_client

    def classify(
        self,
        *,
        title: str,
        url: str,
        filename: str = "",
        page_text: str = "",
        pre_score: int = 0,
        pre_reasons: list[str] | None = None,
    ) -> Candidate:
        pre_reasons = pre_reasons or []
        text = " ".join([title, filename, url, page_text[:1000], " ".join(pre_reasons)]).lower()
        brand = next((b.title() for b in BRANDS if b in text), "")
        keyword_hits = [k for k in KEYWORDS if k in text]
        ext = self._extension(filename or url)

        rule_confidence = min(0.95, max(0.05, pre_score / 24)) if pre_score else 0.0
        semantic_confidence = min(0.85, 0.10 + len(keyword_hits) * 0.10 + (0.25 if brand else 0) + (0.20 if ext else 0))
        confidence = max(rule_confidence, semantic_confidence)
        reason_bits = [*pre_reasons, *keyword_hits]
        if brand:
            reason_bits.append(f"brand:{brand}")
        if ext:
            reason_bits.append(f"extension:{ext}")
        reason_bits = list(dict.fromkeys([x for x in reason_bits if x]))
        reason = "Focused match: " + ", ".join(reason_bits) if reason_bits else "Focused match from source URL."
        risk_note = "Manual review required before archiving."
        kind = "implant_library" if ("implant" in text or brand) else "dental_library"

        # AI is intentionally called only after deterministic filtering. It should enrich the decision,
        # not wander through unrelated links or auto-approve uploads.
        if self.config.ai.enabled and self.ai_client and (pre_score >= 7 or ext or brand):
            ai = self.ai_client.classify_candidate(title=title, url=url, filename=filename, page_text=page_text)
            if ai.reason or ai.confidence > 0:
                confidence = max(confidence, ai.confidence)
                brand = ai.detected_brand or brand
                kind = ai.detected_kind or kind
                reason = ai.reason or reason
                risk_note = ai.risk_note or risk_note

        return Candidate(
            name=filename or title or urlparse(url).netloc or url,
            source_url=url,
            source_type="google_drive" if "drive.google.com" in url else "website",
            detected_brand=brand,
            detected_kind=kind,
            confidence=round(float(confidence), 2),
            reason=reason,
            risk_note=risk_note,
            extension=ext,
            approved=False,
        )

    @staticmethod
    def _extension(value: str) -> str:
        value = value.lower().split("?")[0].split("#")[0]
        for ext in [".zip", ".7z", ".rar", ".stl", ".obj", ".ply", ".xml", ".dme", ".library", ".implant"]:
            if value.endswith(ext):
                return ext
        return ""
