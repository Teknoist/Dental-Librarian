from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


FOCUS_TERMS = {
    "implant": 5,
    "implantlibrary": 7,
    "library": 4,
    "libraries": 4,
    "exocad": 5,
    "cadcam": 4,
    "cad-cam": 4,
    "dental": 3,
    "stl": 4,
    "xml": 3,
    "dme": 3,
    "download": 2,
    "downloads": 2,
}

BRAND_TERMS = {
    "osstem": 8,
    "straumann": 8,
    "nobel": 8,
    "megagen": 8,
    "dentsply": 7,
    "medentika": 7,
    "biohorizons": 7,
    "zimmer": 7,
    "mis": 6,
    "neodent": 7,
    "camlog": 7,
    "bego": 6,
    "bredent": 6,
    "icx": 6,
    "ankylos": 7,
}

FILE_EXT_SCORES = {
    ".zip": 12,
    ".7z": 12,
    ".rar": 12,
    ".stl": 10,
    ".obj": 8,
    ".ply": 8,
    ".xml": 7,
    ".dme": 9,
    ".library": 12,
    ".implant": 12,
}

NEGATIVE_TERMS = {
    "login": -10,
    "signin": -10,
    "signup": -10,
    "register": -8,
    "privacy": -8,
    "terms": -8,
    "contact": -7,
    "about": -6,
    "cart": -10,
    "checkout": -10,
    "facebook": -7,
    "instagram": -7,
    "youtube": -7,
    "linkedin": -7,
    "cookie": -8,
    "wp-content/uploads": -2,
}

SKIP_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".css", ".js", ".map", ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
}


@dataclass(frozen=True)
class LinkScore:
    score: int
    reasons: list[str]
    extension: str
    should_visit: bool
    should_classify: bool
    should_candidate: bool


def _ext_from_url(url: str) -> str:
    path = urlparse(url).path.lower().split("?")[0].split("#")[0]
    for ext in [*FILE_EXT_SCORES.keys(), *SKIP_EXTENSIONS]:
        if path.endswith(ext):
            return ext
    return ""


def score_link(url: str, link_text: str = "", page_title: str = "") -> LinkScore:
    parsed = urlparse(url)
    haystack = " ".join([url, parsed.path, link_text, page_title]).lower()
    reasons: list[str] = []
    score = 0
    ext = _ext_from_url(url)

    if ext in SKIP_EXTENSIONS:
        return LinkScore(-99, [f"skip extension {ext}"], ext, False, False, False)

    if "drive.google.com" in parsed.netloc:
        score += 14
        reasons.append("google drive")
        if "/folders/" in url:
            score += 6
            reasons.append("drive folder")

    if ext in FILE_EXT_SCORES:
        score += FILE_EXT_SCORES[ext]
        reasons.append(f"file extension {ext}")

    for term, points in FOCUS_TERMS.items():
        if term in haystack:
            score += points
            reasons.append(term)

    for brand, points in BRAND_TERMS.items():
        if brand in haystack:
            score += points
            reasons.append(f"brand:{brand}")

    for term, points in NEGATIVE_TERMS.items():
        if term in haystack:
            score += points
            reasons.append(f"negative:{term}")

    should_candidate = score >= 10 or bool(ext in FILE_EXT_SCORES)
    should_classify = score >= 7
    should_visit = score >= 3 and not should_candidate and parsed.netloc != ""

    return LinkScore(score, reasons, ext, should_visit, should_classify, should_candidate)
