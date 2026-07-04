from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


CandidateStatus = Literal["candidate", "approved", "rejected", "downloaded", "packaged", "uploaded", "error"]
SourceType = Literal["website", "google_drive", "file", "unknown"]


class Candidate(BaseModel):
    name: str
    source_url: str
    source_type: SourceType = "unknown"
    detected_brand: str = ""
    detected_kind: str = ""
    confidence: float = 0.0
    reason: str = ""
    risk_note: str = ""
    extension: str = ""
    size_bytes: int | None = None
    approved: bool = False
    status: CandidateStatus = "candidate"
    local_path: str | None = None
    archive_path: str | None = None
    ia_identifier: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ArchiveRecord(BaseModel):
    name: str
    title: str
    source_url: str
    source_type: SourceType
    archive_url: str
    identifier: str
    sha256: str
    size_bytes: int
    subject: list[str] = Field(default_factory=list)
    description: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FileManifestEntry(BaseModel):
    name: str
    size_bytes: int
    sha256: str


class PackageManifest(BaseModel):
    title: str
    source_url: str
    source_type: SourceType
    archived_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    files: list[FileManifestEntry] = Field(default_factory=list)
