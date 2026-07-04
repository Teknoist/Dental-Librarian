from __future__ import annotations

import json
from pathlib import Path

from src.core.models import ArchiveRecord, Candidate


def ensure_data_files(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in ["archive_candidates.json", "archive.json", "sources.yaml"]:
        path = data_dir / name
        if not path.exists():
            path.write_text("[]\n" if name.endswith(".json") else "sources: []\n", encoding="utf-8")


def load_candidates(path: Path) -> list[Candidate]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8") or "[]")
    return [Candidate.model_validate(x) for x in raw]


def save_candidates(path: Path, candidates: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([c.model_dump() for c in candidates], ensure_ascii=False, indent=2), encoding="utf-8")


def load_archive(path: Path) -> list[ArchiveRecord]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8") or "[]")
    return [ArchiveRecord.model_validate(x) for x in raw]


def save_archive(path: Path, records: list[ArchiveRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([r.model_dump() for r in records], ensure_ascii=False, indent=2), encoding="utf-8")
