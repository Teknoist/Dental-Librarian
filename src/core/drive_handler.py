from __future__ import annotations

from pathlib import Path
from typing import Callable

import gdown
from slugify import slugify

LogFn = Callable[[str, str], None]


class GoogleDriveHandler:
    def __init__(self, download_root: Path, allowed_extensions: list[str], log: LogFn | None = None) -> None:
        self.download_root = download_root
        self.allowed_extensions = {e.lower() for e in allowed_extensions}
        self.log = log or (lambda level, msg: None)

    @staticmethod
    def is_drive_folder(url: str) -> bool:
        return "drive.google.com" in url and "/folders/" in url

    def download_public_folder(self, url: str, title: str = "google-drive-folder") -> Path:
        if not self.is_drive_folder(url):
            raise ValueError("Not a Google Drive folder URL")

        target = self.download_root / slugify(title or "google-drive-folder")
        target.mkdir(parents=True, exist_ok=True)

        self.log("INFO", f"Google Drive public folder download started: {url}")
        self.log("INFO", f"Download target: {target}")

        try:
            gdown.download_folder(url=url, output=str(target), quiet=False, use_cookies=False)
        except Exception as exc:
            raise RuntimeError(f"Google Drive folder download failed: {exc}") from exc

        files = [p for p in target.rglob("*") if p.is_file()]
        allowed = [p for p in files if p.suffix.lower() in self.allowed_extensions]
        skipped = len(files) - len(allowed)

        if skipped:
            self.log("WARN", f"Skipped {skipped} files because extension is not allowed.")
        if not allowed:
            self.log("WARN", "No allowed files found in Drive folder. Keeping downloaded folder for review.")
        else:
            self.log("INFO", f"Allowed files found: {len(allowed)}")

        return target
