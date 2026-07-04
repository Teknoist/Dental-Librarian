from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Callable

from slugify import slugify

from src.core.models import FileManifestEntry, PackageManifest
from src.utils.checksum import sha256_file

LogFn = Callable[[str, str], None]


class ArchivePacker:
    def __init__(self, archive_root: Path, allowed_extensions: list[str], log: LogFn | None = None) -> None:
        self.archive_root = archive_root
        self.allowed_extensions = {e.lower() for e in allowed_extensions}
        self.log = log or (lambda level, msg: None)

    def package_folder(self, folder: Path, *, title: str, source_url: str, source_type: str) -> Path:
        if not folder.exists() or not folder.is_dir():
            raise FileNotFoundError(folder)

        self.archive_root.mkdir(parents=True, exist_ok=True)
        slug = slugify(title) or "dental-library-package"
        package_dir = self.archive_root / slug
        package_dir.mkdir(parents=True, exist_ok=True)

        files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in self.allowed_extensions]
        if not files:
            raise RuntimeError("No allowed files found to package.")

        manifest = PackageManifest(title=title, source_url=source_url, source_type=source_type)
        checksums: list[str] = []

        for p in files:
            digest = sha256_file(p)
            rel = p.relative_to(folder).as_posix()
            manifest.files.append(FileManifestEntry(name=rel, size_bytes=p.stat().st_size, sha256=digest))
            checksums.append(f"{digest}  {rel}")

        (package_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        (package_dir / "source.txt").write_text(source_url + "\n", encoding="utf-8")
        (package_dir / "checksums.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")

        zip_path = self.archive_root / f"{slug}.zip"
        self.log("INFO", f"Creating ZIP: {zip_path}")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in files:
                zf.write(p, p.relative_to(folder).as_posix())
            zf.write(package_dir / "manifest.json", "manifest.json")
            zf.write(package_dir / "source.txt", "source.txt")
            zf.write(package_dir / "checksums.sha256", "checksums.sha256")

        self.log("INFO", f"ZIP created: {zip_path.name} ({zip_path.stat().st_size} bytes)")
        return zip_path
