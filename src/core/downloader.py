from __future__ import annotations

from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests
from slugify import slugify

LogFn = Callable[[str, str], None]


class DirectDownloader:
    def __init__(self, download_root: Path, allowed_extensions: list[str], log: LogFn | None = None) -> None:
        self.download_root = download_root
        self.allowed_extensions = {e.lower() for e in allowed_extensions}
        self.log = log or (lambda level, msg: None)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "DentalLibrarian/0.1 public-resource-review"})

    def is_allowed_url(self, url: str) -> bool:
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in self.allowed_extensions)

    def download_file(self, url: str, title: str = "downloaded-resource") -> Path:
        if not self.is_allowed_url(url):
            raise ValueError("URL does not end with an allowed file extension.")

        folder = self.download_root / slugify(title or "downloaded-resource")
        folder.mkdir(parents=True, exist_ok=True)
        filename = Path(urlparse(url).path).name or f"{slugify(title)}.bin"
        target = folder / filename

        self.log("INFO", f"Direct file download started: {url}")
        with self.session.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with target.open("wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        self.log("INFO", f"Downloaded: {target} ({target.stat().st_size} bytes)")
        return folder
