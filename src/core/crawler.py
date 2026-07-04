from __future__ import annotations

import time
from collections import deque
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.core.classifier import CandidateClassifier
from src.core.config import Config
from src.core.models import Candidate

LogFn = Callable[[str, str], None]


class PublicCrawler:
    def __init__(self, config: Config, classifier: CandidateClassifier, log: LogFn | None = None) -> None:
        self.config = config
        self.classifier = classifier
        self.log = log or (lambda level, msg: None)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "DentalLibrarian/0.1 public-resource-review"})

    def scan(self, start_url: str) -> list[Candidate]:
        parsed = urlparse(start_url)
        if parsed.scheme not in {"http", "https"}:
            self.log("ERROR", f"Unsupported URL scheme: {start_url}")
            return []

        if "drive.google.com" in parsed.netloc:
            self.log("INFO", "Google Drive link detected; handing to Drive module.")
            return [self.classifier.classify(title="Google Drive folder", url=start_url, filename="")]

        root_host = parsed.netloc
        queue: deque[str] = deque([start_url])
        seen: set[str] = set()
        found: list[Candidate] = []

        while queue and len(seen) < self.config.app.max_pages_per_source:
            url = queue.popleft()
            if url in seen:
                continue
            seen.add(url)
            self.log("INFO", f"Scanning page: {url}")

            try:
                r = self.session.get(url, timeout=self.config.app.request_timeout_seconds)
                r.raise_for_status()
            except Exception as exc:
                self.log("WARN", f"Could not fetch {url}: {exc}")
                continue

            content_type = r.headers.get("content-type", "")
            if "text/html" not in content_type and "html" not in content_type:
                candidate = self.classifier.classify(title=url, url=url, filename=url.split("/")[-1])
                if candidate.extension:
                    found.append(candidate)
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            title = (soup.title.string.strip() if soup.title and soup.title.string else url)
            page_text = soup.get_text(" ", strip=True)[:3000]

            for a in soup.select("a[href]"):
                href = a.get("href", "").strip()
                if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                    continue
                abs_url = urljoin(url, href)
                p = urlparse(abs_url)
                if p.scheme not in {"http", "https"}:
                    continue
                link_text = a.get_text(" ", strip=True)
                filename = p.path.rstrip("/").split("/")[-1] or link_text or abs_url
                candidate = self.classifier.classify(title=link_text or title, url=abs_url, filename=filename, page_text=page_text)

                if candidate.extension or candidate.confidence >= 0.45 or "drive.google.com" in p.netloc:
                    self.log("INFO", f"Candidate found: {candidate.name} ({candidate.confidence})")
                    found.append(candidate)
                    continue

                if p.netloc == root_host and abs_url not in seen and len(seen) + len(queue) < self.config.app.max_pages_per_source:
                    queue.append(abs_url)

            time.sleep(max(0, self.config.app.polite_delay_seconds))

        self.log("INFO", f"Scan completed. Candidates: {len(found)}")
        return found
