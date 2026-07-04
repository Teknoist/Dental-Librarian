from __future__ import annotations

from pathlib import Path
from typing import Callable

from slugify import slugify

from src.core.config import Config
from src.core.models import ArchiveRecord
from src.utils.checksum import sha256_file

LogFn = Callable[[str, str], None]


class InternetArchiveUploader:
    def __init__(self, config: Config, log: LogFn | None = None) -> None:
        self.config = config
        self.log = log or (lambda level, msg: None)

    def build_identifier(self, title: str, zip_path: Path) -> str:
        digest = sha256_file(zip_path)[:8]
        base = slugify(title) or "dental-cadcam-library"
        if not base.startswith("dental-cadcam-library"):
            base = f"dental-cadcam-library-{base}"
        return f"{base}-{digest}"[:80]

    def upload(self, *, zip_path: Path, title: str, source_url: str, source_type: str) -> ArchiveRecord:
        if not self.config.internet_archive.enabled:
            raise RuntimeError("Internet Archive upload is disabled in config.yaml")
        if not zip_path.exists():
            raise FileNotFoundError(zip_path)

        import internetarchive as ia

        identifier = self.build_identifier(title, zip_path)
        sha = sha256_file(zip_path)
        metadata = {
            "title": title,
            "creator": self.config.internet_archive.creator,
            "collection": self.config.internet_archive.collection,
            "mediatype": self.config.internet_archive.mediatype,
            "subject": "; ".join(self.config.internet_archive.subject),
            "description": "Archived copy of a freely available dental CAD/CAM library resource. Original source URL is preserved for attribution.",
            "source": source_url,
        }

        self.log("INFO", f"Internet Archive upload started: {identifier}")
        ia.upload(identifier, files=[str(zip_path)], metadata=metadata, verbose=True, retries=3)
        archive_url = f"https://archive.org/details/{identifier}"
        self.log("INFO", f"Internet Archive upload completed: {archive_url}")

        return ArchiveRecord(
            name=zip_path.name,
            title=title,
            source_url=source_url,
            source_type=source_type,
            archive_url=archive_url,
            identifier=identifier,
            sha256=sha,
            size_bytes=zip_path.stat().st_size,
            subject=self.config.internet_archive.subject,
            description=metadata["description"],
        )
