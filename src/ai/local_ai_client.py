from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class AIResult:
    is_candidate: bool
    confidence: float
    detected_brand: str
    detected_kind: str
    reason: str
    risk_note: str = ""


class LocalAIClient:
    def __init__(self, base_url: str, model: str, temperature: float = 0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature

    def healthcheck(self) -> tuple[bool, str]:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=10)
            r.raise_for_status()
            models = [m.get("name", "") for m in r.json().get("models", [])]
            if self.model not in models:
                return False, f"Ollama çalışıyor ama model bulunamadı: {self.model}. Yüklüler: {', '.join(models) or 'yok'}"
            return True, f"Ollama hazır: {self.model}"
        except Exception as exc:
            return False, f"Ollama bağlantı hatası: {exc}"

    def classify_candidate(self, *, title: str, url: str, filename: str = "", page_text: str = "") -> AIResult:
        prompt = f"""
You are the classifier module of a local app called Dental Librarian.

Task:
Evaluate whether the provided source looks like a public dental CAD/CAM implant library candidate.

Return only valid JSON. Do not add markdown.

JSON schema:
{{
  "is_candidate": true,
  "confidence": 0.0,
  "detected_brand": "",
  "detected_kind": "",
  "reason": "",
  "risk_note": ""
}}

Rules:
- Prefer candidates that mention implant, exocad, cadcam, library, stl, xml, Osstem, Straumann, Nobel, MegaGen, Dentsply, Medentika, BioHorizons, Zimmer, MIS, Neodent.
- If login/private/paywalled/unclear license is likely, set risk_note.
- If uncertain, keep confidence low.
- Do not approve upload. Only classify.

Title: {title}
Filename: {filename}
URL: {url}
Page text excerpt: {page_text[:2500]}
"""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a safe JSON-only classification engine."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": self.temperature},
        }
        try:
            r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
            r.raise_for_status()
            content = r.json().get("message", {}).get("content", "{}")
            data = json.loads(content)
            return AIResult(
                is_candidate=bool(data.get("is_candidate", False)),
                confidence=float(data.get("confidence", 0.0) or 0.0),
                detected_brand=str(data.get("detected_brand", "") or ""),
                detected_kind=str(data.get("detected_kind", "") or ""),
                reason=str(data.get("reason", "") or ""),
                risk_note=str(data.get("risk_note", "") or ""),
            )
        except Exception as exc:
            return AIResult(
                is_candidate=False,
                confidence=0.0,
                detected_brand="",
                detected_kind="",
                reason="Local AI could not return valid JSON.",
                risk_note=str(exc),
            )
