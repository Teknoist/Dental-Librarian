from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ai.local_ai_client import LocalAIClient
from src.core.classifier import CandidateClassifier
from src.core.config import Config
from src.core.crawler import PublicCrawler
from src.core.drive_handler import GoogleDriveHandler
from src.core.models import Candidate
from src.core.packer import ArchivePacker
from src.core.storage import ensure_data_files, load_archive, load_candidates, save_archive, save_candidates
from src.core.ia_uploader import InternetArchiveUploader


class ScanWorker(QObject):
    log = Signal(str, str)
    done = Signal(list)
    failed = Signal(str)

    def __init__(self, url: str, config: Config) -> None:
        super().__init__()
        self.url = url
        self.config = config

    def run(self) -> None:
        try:
            ai = LocalAIClient(self.config.ai.base_url, self.config.ai.model, self.config.ai.temperature)
            classifier = CandidateClassifier(self.config, ai_client=ai)
            crawler = PublicCrawler(self.config, classifier, log=lambda lvl, msg: self.log.emit(lvl, msg))
            candidates = crawler.scan(self.url)
            self.done.emit([c.model_dump() for c in candidates])
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, *, root: Path, config: Config) -> None:
        super().__init__()
        self.root = root
        self.config = config
        self.setWindowTitle(config.app.name)

        self.data_dir = root / config.archive.data_dir
        self.download_dir = root / config.archive.download_dir
        self.archive_dir = root / config.archive.output_dir
        ensure_data_files(self.data_dir)
        self.candidates_path = self.data_dir / "archive_candidates.json"
        self.archive_path = self.data_dir / "archive.json"
        self.candidates: list[Candidate] = load_candidates(self.candidates_path)

        self._worker_thread: QThread | None = None
        self._worker: ScanWorker | None = None

        self._build_ui()
        self._apply_theme()
        self.refresh_table()
        self.log("INFO", "Dental Librarian ready.")
        self.log("INFO", f"AI model: {self.config.ai.model} at {self.config.ai.base_url}")
        self.log("INFO", "Default mode: candidate review first, upload disabled until config enables it.")

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        title = QLabel("Dental Librarian")
        title.setObjectName("Title")
        layout.addWidget(title)

        top = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Website or public Google Drive folder URL")
        self.scan_btn = QPushButton("Scan")
        self.ai_btn = QPushButton("Test Local AI")
        self.approve_btn = QPushButton("Approve Selected")
        self.reject_btn = QPushButton("Reject Selected")
        self.pack_btn = QPushButton("Download + ZIP Selected")
        self.upload_btn = QPushButton("Upload Selected to IA")
        self.dry_run = QCheckBox("Dry run")
        self.dry_run.setChecked(self.config.app.dry_run)

        top.addWidget(self.url_input, 1)
        top.addWidget(self.scan_btn)
        top.addWidget(self.ai_btn)
        top.addWidget(self.approve_btn)
        top.addWidget(self.reject_btn)
        top.addWidget(self.pack_btn)
        top.addWidget(self.upload_btn)
        top.addWidget(self.dry_run)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Status", "Name", "Brand", "Kind", "Confidence", "Source", "Reason", "Risk"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        splitter.addWidget(self.table)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        right_layout.addWidget(QLabel("Live log"))
        right_layout.addWidget(self.log_box, 1)
        splitter.addWidget(right)
        splitter.setSizes([880, 400])

        self.scan_btn.clicked.connect(self.start_scan)
        self.ai_btn.clicked.connect(self.test_ai)
        self.approve_btn.clicked.connect(lambda: self.set_selected_approval(True))
        self.reject_btn.clicked.connect(lambda: self.set_selected_approval(False, reject=True))
        self.pack_btn.clicked.connect(self.package_selected)
        self.upload_btn.clicked.connect(self.upload_selected)

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #080914; color: #f5f7ff; font-family: Segoe UI, Arial; }
            QLabel#Title { font-size: 28px; font-weight: 900; padding: 8px 0; }
            QLineEdit, QTextEdit, QTableWidget { background: rgba(255,255,255,.07); color: #f5f7ff; border: 1px solid rgba(255,255,255,.14); border-radius: 12px; padding: 8px; }
            QPushButton { background: rgba(139,124,255,.18); color: #f5f7ff; border: 1px solid rgba(139,124,255,.35); border-radius: 12px; padding: 9px 12px; font-weight: 800; }
            QPushButton:hover { background: rgba(139,124,255,.28); }
            QHeaderView::section { background: #15182d; color: #f5f7ff; padding: 8px; border: 0; }
            QTableWidget::item { padding: 8px; }
            QCheckBox { spacing: 8px; }
            """
        )

    def log(self, level: str, message: str) -> None:
        color = {"INFO": "#9ee8c9", "WARN": "#ffd166", "ERROR": "#ff6b8a", "AI": "#9bb5ff"}.get(level, "#f5f7ff")
        self.log_box.append(f'<span style="color:{color};font-weight:700">[{level}]</span> {message}')

    def refresh_table(self) -> None:
        self.table.setRowCount(len(self.candidates))
        for row, c in enumerate(self.candidates):
            values = [c.status, c.name, c.detected_brand, c.detected_kind, f"{c.confidence:.2f}", c.source_type, c.reason, c.risk_note]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c.approved:
                    item.setBackground(QColor(24, 70, 48))
                elif c.status == "rejected":
                    item.setBackground(QColor(70, 35, 45))
                self.table.setItem(row, col, item)

    def selected_indexes(self) -> list[int]:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [r for r in rows if 0 <= r < len(self.candidates)]

    def save_candidates(self) -> None:
        save_candidates(self.candidates_path, self.candidates)
        self.refresh_table()

    def test_ai(self) -> None:
        ai = LocalAIClient(self.config.ai.base_url, self.config.ai.model, self.config.ai.temperature)
        ok, msg = ai.healthcheck()
        self.log("AI" if ok else "ERROR", msg)
        if not ok:
            QMessageBox.warning(self, "Ollama", msg)

    def start_scan(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Add a website or public Google Drive folder URL first.")
            return
        self.scan_btn.setEnabled(False)
        self.log("INFO", f"Scan started: {url}")
        self._worker_thread = QThread()
        self._worker = ScanWorker(url, self.config)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.log.connect(self.log)
        self._worker.done.connect(self.scan_done)
        self._worker.failed.connect(self.scan_failed)
        self._worker.done.connect(self._worker_thread.quit)
        self._worker.failed.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(lambda: self.scan_btn.setEnabled(True))
        self._worker_thread.start()

    def scan_done(self, raw_candidates: list[dict]) -> None:
        new_candidates = [Candidate.model_validate(x) for x in raw_candidates]
        existing = {c.source_url for c in self.candidates}
        added = 0
        for c in new_candidates:
            if c.source_url not in existing:
                self.candidates.append(c)
                existing.add(c.source_url)
                added += 1
                self.log("AI", f"Candidate: {c.name} | confidence={c.confidence} | {c.reason}")
        self.save_candidates()
        self.log("INFO", f"Scan finished. New candidates: {added}")

    def scan_failed(self, error: str) -> None:
        self.log("ERROR", error)
        QMessageBox.critical(self, "Scan failed", error)

    def set_selected_approval(self, approved: bool, reject: bool = False) -> None:
        rows = self.selected_indexes()
        if not rows:
            return
        for r in rows:
            self.candidates[r].approved = approved
            self.candidates[r].status = "approved" if approved else ("rejected" if reject else "candidate")
            self.log("INFO", f"{self.candidates[r].status.title()}: {self.candidates[r].name}")
        self.save_candidates()

    def package_selected(self) -> None:
        rows = self.selected_indexes()
        if not rows:
            return
        drive = GoogleDriveHandler(self.download_dir, self.config.archive.allowed_extensions, log=self.log)
        packer = ArchivePacker(self.archive_dir, self.config.archive.allowed_extensions, log=self.log)
        for r in rows:
            c = self.candidates[r]
            if self.config.app.require_manual_approval and not c.approved:
                self.log("WARN", f"Not approved, skipped: {c.name}")
                continue
            if c.source_type == "google_drive" and drive.is_drive_folder(c.source_url):
                folder = drive.download_public_folder(c.source_url, title=c.name or "drive-folder")
                zip_path = packer.package_folder(folder, title=c.name or "Dental Library", source_url=c.source_url, source_type=c.source_type)
                c.local_path = str(folder)
                c.archive_path = str(zip_path)
                c.status = "packaged"
                self.log("INFO", f"Packaged: {zip_path}")
            else:
                self.log("WARN", f"Direct file download is not implemented for this source yet: {c.source_url}")
        self.save_candidates()

    def upload_selected(self) -> None:
        rows = self.selected_indexes()
        if not rows:
            return
        if self.dry_run.isChecked():
            self.log("WARN", "Dry run is enabled. Upload skipped.")
            return
        uploader = InternetArchiveUploader(self.config, log=self.log)
        records = load_archive(self.archive_path)
        for r in rows:
            c = self.candidates[r]
            if not c.approved:
                self.log("WARN", f"Not approved, skipped upload: {c.name}")
                continue
            if not c.archive_path:
                self.log("WARN", f"No ZIP package yet: {c.name}")
                continue
            record = uploader.upload(zip_path=Path(c.archive_path), title=c.name, source_url=c.source_url, source_type=c.source_type)
            c.ia_identifier = record.identifier
            c.status = "uploaded"
            records.append(record)
        save_archive(self.archive_path, records)
        self.save_candidates()

    def closeEvent(self, event) -> None:
        self.save_candidates()
        super().closeEvent(event)
