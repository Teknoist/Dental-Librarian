from __future__ import annotations

import time
from collections import deque
from typing import Callable
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

from src.core.classifier import CandidateClassifier
from src.core.config import Config
from src.core.link_scoring import score_link
from src.core.models import Candidate

LogFn = Callable[[str, str], None]


class PublicCrawler:
    def __init__(self, config: Config, classifier: CandidateClassifier, log: LogFn | None = None) -> None:
        self.config = config
        self.classifier = classifier
        self.log = log or (lambda level, msg: None)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "DentalLibrarian/0.2 focused-public-resource-review"})

    def scan(self, start_url: str) -> list[Candidate]:
        parsed = urlparse(start_url)
        if parsed.scheme not in {"http", "https"}:
            self.log("ERROR", f"Unsupported URL scheme: {start_url}")
            return []

        start_score = score_link(start_url, page_title=start_url)
        if "drive.google.com" in parsed.netloc:
            self.log("INFO", f"Google Drive link detected. score={start_score.score} reasons={', '.join(start_score.reasons)}")
            return [self.classifier.classify(title="Google Drive folder", url=start_url, filename="", pre_score=start_score.score, pre_reasons=start_score.reasons)]

        root_host = parsed.netloc
        queue: deque[str] = deque([start_url])
        seen: set[str] = set()
        found: list[Candidate] = []
        candidate_urls: set[str] = set()

        while queue and len(seen) < self.config.app.max_pages_per_source:
            url = queue.popleft()
            url = urldefrag(url).url
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
                filename = urlparse(url).path.rstrip("/").split("/")[-1]
                link_score = score_link(url, filename, url)
                if link_score.should_candidate:
                    candidate = self.classifier.classify(
                        title=filename or url,
                        url=url,
                        filename=filename,
                        pre_score=link_score.score,
                        pre_reasons=link_score.reasons,
                    )
                    found.append(candidate)
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            title = (soup.title.string.strip() if soup.title and soup.title.string else url)
            page_text = soup.get_text(" ", strip=True)[:3000]

            ranked_links: list[tuple[int, str, str, str, object]] = []
            for a in soup.select("a[href]"):
                href = a.get("href", "").strip()
                if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                    continue
                abs_url = urldefrag(urljoin(url, href)).url
                p = urlparse(abs_url)
                if p.scheme not in {"http", "https"}:
                    continue
                link_text = a.get_text(" ", strip=True)
                filename = p.path.rstrip("/").split("/")[-1] or link_text or abs_url
                link_score = score_link(abs_url, link_text, title)
                if link_score.score <= 0:
                    continue
                ranked_links.append((link_score.score, abs_url, link_text, filename, link_score))

            ranked_links.sort(key=lambda x: x[0], reverse=True)
            self.log("INFO", f"Focused links kept: {len(ranked_links)}")

            for _, abs_url, link_text, filename, link_score in ranked_links:
                p = urlparse(abs_url)

                if link_score.should_candidate and abs_url not in candidate_urls:
                    candidate_urls.add(abs_url)
                    candidate = self.classifier.classify(
                        title=link_text or title,
                        url=abs_url,
                        filename=filename,
                        page_text=page_text if link_score.should_classify else "",
                        pre_score=link_score.score,
                        pre_reasons=link_score.reasons,
                    )
                    self.log("INFO", f"Candidate found: {candidate.name} score={link_score.score} confidence={candidate.confidence} reasons={', '.join(link_score.reasons)}")
                    found.append(candidate)
                    continue

                if (
                    link_score.should_visit
                    and p.netloc == root_host
                    and abs_url not in seen
                    and len(seen) + len(queue) < self.config.app.max_pages_per_source
                ):
                    self.log("INFO", f"Queued focused page: {abs_url} score={link_score.score}")
                    queue.append(abs_url)

            time.sleep(max(0, self.config.app.polite_delay_seconds))

        self.log("INFO", f"Scan completed. Candidates: {len(found)}")
        return found
