# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2026 Aaron Soria

import os

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QFileDialog, QHeaderView, QMessageBox, QTableWidgetItem

from Libs.ImageScanner import (
    DEFAULT_DETECTION_SCORE,
    DEFAULT_FACE_THRESHOLD,
    DEFAULT_NUDITY_THRESHOLD,
    EXPLICIT_CLASSES,
    AppendToLog,
    BuildFaceEncodings,
    CollectImageFiles,
    CopyToResults,
    CreateSessionLog,
    FaceModels,
    LoadNudityDetector,
    MakeLogEntry,
    MakeSessionEnd,
    ReadImage,
    RecognizeFaces,
    ScanNudity,
)
from Views.PAnalizerView_ui import Ui_MainWindow


# ──────────────────────────────────────────────
# Workers — run in a background thread so the UI stays responsive
# ──────────────────────────────────────────────

class ScanWorker(QThread):
    progress = pyqtSignal(int, int)         # (files processed, total files)
    result_found = pyqtSignal(str, float, str)  # (matching file, score, copied to or "")
    log_created = pyqtSignal(str)           # path of the session log
    status_message = pyqtSignal(str)
    failed = pyqtSignal(str)                # error that stopped the scan
    scan_finished = pyqtSignal(int, int)    # (files analyzed, matches)

    scan_type = None

    def __init__(self, search_path, result_path):
        super().__init__()
        self.search_path = search_path
        self.result_path = result_path
        self._stop = False
        self._analyzed = 0
        self._matches = 0
        self.stopped = False

    def stop(self):
        self._stop = True

    def settings(self):
        return {"search_directory": self.search_path}

    def prepare(self):
        """Load models before scanning. Raise to abort the scan."""

    def analyze(self, image):
        """Return (is_match, details) for a BGR image."""
        raise NotImplementedError

    def score(self, details):
        """Return the score shown for a match (higher means stronger)."""
        raise NotImplementedError

    def run(self):
        try:
            self._scan()
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            self.scan_finished.emit(self._analyzed, self._matches)

    def _scan(self):
        self.prepare()
        image_files = CollectImageFiles(self.search_path)
        total = len(image_files)
        if total == 0:
            self.status_message.emit("No images found in the search directory.")
            return

        log_path = CreateSessionLog(self.result_path, self.scan_type, self.settings())
        self.log_created.emit(log_path)
        self.progress.emit(0, total)
        for i, file_path in enumerate(image_files):
            if self._stop:
                self.stopped = True
                break
            self.status_message.emit(f"Analyzing: {os.path.basename(file_path)}")
            AppendToLog(log_path, self._process(file_path))
            self._analyzed += 1
            self.progress.emit(i + 1, total)

        AppendToLog(log_path, MakeSessionEnd(total, self._analyzed, self._matches, self.stopped))
        stopped = " (stopped)" if self.stopped else ""
        self.status_message.emit(
            f"Done{stopped}. {self._matches} match(es) in {self._analyzed} of {total} image(s). Log: {log_path}"
        )

    def _process(self, file_path):
        image = ReadImage(file_path)
        if image is None:
            return MakeLogEntry(file_path, False, error="could not decode image")
        try:
            is_match, details = self.analyze(image)
        except Exception as e:
            return MakeLogEntry(file_path, False, error=f"{type(e).__name__}: {e}")
        copied_to, error = None, None
        if is_match:
            self._matches += 1
            try:
                copied_to = CopyToResults(file_path, self.result_path)
            except OSError as e:
                error = f"copy failed: {e}"
            self.result_found.emit(file_path, self.score(details), copied_to or "")
        return MakeLogEntry(file_path, is_match, details, copied_to=copied_to, error=error)


class NudityWorker(ScanWorker):
    scan_type = "nudity"

    def __init__(self, search_path, result_path, threshold=DEFAULT_NUDITY_THRESHOLD):
        super().__init__(search_path, result_path)
        self.threshold = threshold
        self.detector = None

    def settings(self):
        return {**super().settings(), "model": "NudeNet 3.x NudeDetector", "threshold": self.threshold}

    def prepare(self):
        self.status_message.emit("Loading nudity detection model...")
        self.detector = LoadNudityDetector()

    def analyze(self, image):
        is_explicit, detections = ScanNudity(image, threshold=self.threshold, detector=self.detector)
        return is_explicit, {"detections": detections}

    def score(self, details):
        return max((d["score"] for d in details["detections"] if d["class"] in EXPLICIT_CLASSES), default=0.0)


class FaceWorker(ScanWorker):
    scan_type = "face"

    def __init__(self, search_path, learn_path, result_path, threshold=DEFAULT_FACE_THRESHOLD):
        super().__init__(search_path, result_path)
        self.learn_path = learn_path
        self.threshold = threshold
        self.models = None
        self.reference_features = []
        self.reference_files = []

    def settings(self):
        return {
            **super().settings(),
            "model": "OpenCV YuNet 2023mar + SFace 2021dec",
            "threshold_cosine": self.threshold,
            "detection_confidence": DEFAULT_DETECTION_SCORE,
            "reference_directory": self.learn_path,
            "reference_files": self.reference_files,
        }

    def prepare(self):
        self.status_message.emit("Loading face models and reference photos...")
        self.models = FaceModels()
        self.reference_features, self.reference_files = BuildFaceEncodings(self.learn_path, self.models)
        if not self.reference_features:
            raise RuntimeError(
                "No face was detected in the reference photos. "
                "Add clear photos of the person's face and try again."
            )
        self.status_message.emit(f"{len(self.reference_features)} reference face(s) loaded. Searching...")

    def analyze(self, image):
        found, faces = RecognizeFaces(image, self.reference_features, self.models, threshold=self.threshold)
        return found, {"faces": faces}

    def score(self, details):
        return max((f["similarity"] for f in details["faces"]), default=0.0)


# ──────────────────────────────────────────────
# Main window
# ──────────────────────────────────────────────

STYLE_SHEET = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Views", "style.qss")


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)
        self.setupUi(self)
        with open(STYLE_SHEET, encoding="utf-8") as f:
            self.setStyleSheet(f.read())
        self._worker = None
        self._log_path = None
        self._search_root = ""
        self._failed = False

        header = self.ResultsTable.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.ResultsTable.horizontalHeaderItem(1).setToolTip(
            "Nudity screening: highest explicit-content detection score (0-1).\n"
            "Face search: highest similarity to the reference faces (cosine, -1 to 1)."
        )

        self.SearchDirectoryButton.clicked.connect(self.OnSearchDirectoryButtonClick)
        self.SearchLearnButton.clicked.connect(self.OnSearchLearnButtonClick)
        self.SearchResultButton.clicked.connect(self.OnLearnResultButtonClick)
        self.FaceSearchButton.clicked.connect(self.OnFaceSearchButtonClick)
        self.NudeSearchButton.clicked.connect(self.OnNudeSearchButtonClick)
        self.StopButton.clicked.connect(self.OnStopButtonClick)
        self.OpenResultsButton.clicked.connect(self.OpenResultsFolder)
        self.OpenLogButton.clicked.connect(self.OpenLog)
        self.actionOpenResults.triggered.connect(self.OpenResultsFolder)
        self.actionOpenLog.triggered.connect(self.OpenLog)
        self.actionQuit.triggered.connect(self.close)
        self.DirectoryResult.textChanged.connect(self._update_open_buttons)

    # ── Folder selection ──

    def _browse(self, line_edit, caption):
        d = QFileDialog.getExistingDirectory(self, caption, line_edit.text().strip())
        if d:
            line_edit.setText(os.path.normpath(d))
            line_edit.setCursorPosition(0)

    def OnSearchDirectoryButtonClick(self):
        self._browse(self.DirectorySearch, "Images to analyze")

    def OnSearchLearnButtonClick(self):
        self._browse(self.DirectoryLearn, "Reference photos of the person of interest")

    def OnLearnResultButtonClick(self):
        self._browse(self.DirectoryResult, "Results folder")

    # ── Validation ──

    def _validate_paths(self, require_learn=False):
        search = self.DirectorySearch.text().strip()
        result = self.DirectoryResult.text().strip()
        learn = self.DirectoryLearn.text().strip()

        error = None
        if not os.path.isdir(search):
            error = "Choose an existing folder of images to analyze."
        elif not os.path.isdir(result):
            error = "Choose an existing results folder."
        elif os.path.normcase(os.path.abspath(search)) == os.path.normcase(os.path.abspath(result)):
            error = "The folder to analyze and the results folder must be different."
        elif require_learn and not os.path.isdir(learn):
            error = "Choose an existing folder of reference photos."
        if error:
            QMessageBox.warning(self, "PAnalizer", error)
            return None
        return {"search": search, "result": result, "learn": learn}

    # ── Worker lifecycle ──

    def _set_ui_running(self, running):
        for widget in (self.FaceSearchButton, self.NudeSearchButton, self.SearchDirectoryButton,
                       self.SearchLearnButton, self.SearchResultButton, self.DirectorySearch,
                       self.DirectoryLearn, self.DirectoryResult):
            widget.setEnabled(not running)
        self.StopButton.setEnabled(running)

    def _start(self, worker, message):
        self.ResultsTable.setRowCount(0)
        self.progressBar.setRange(0, 0)  # busy indicator until the image count is known
        self.progressLabel.setText("Preparing…")
        self._search_root = worker.search_path
        self._log_path = None
        self._failed = False
        self._update_open_buttons()
        self._set_ui_running(True)
        self.statusbar.showMessage(message)
        self._worker = worker
        worker.progress.connect(self._on_progress)
        worker.result_found.connect(self._on_result_found)
        worker.log_created.connect(self._on_log_created)
        worker.status_message.connect(self.statusbar.showMessage)
        worker.failed.connect(self._on_failed)
        worker.scan_finished.connect(self._on_finished)
        worker.start()

    def _matches_text(self):
        n = self.ResultsTable.rowCount()
        return f"{n} match" if n == 1 else f"{n} matches"

    def _on_progress(self, done, total):
        self.progressBar.setRange(0, max(total, 1))
        self.progressBar.setValue(done)
        self.progressLabel.setText(f"{done:,} / {total:,} images · {self._matches_text()}")

    def _on_result_found(self, path, score, copied_to):
        row = self.ResultsTable.rowCount()
        self.ResultsTable.insertRow(row)
        try:
            shown = os.path.relpath(path, self._search_root)
        except ValueError:
            shown = path
        cells = (
            (shown, path),
            (f"{score:.2f}", None),
            (os.path.basename(copied_to) if copied_to else "copy failed", copied_to or "See the log for details."),
        )
        for column, (text, tooltip) in enumerate(cells):
            item = QTableWidgetItem(text)
            if tooltip:
                item.setToolTip(tooltip)
            if column == 1:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.ResultsTable.setItem(row, column, item)

    def _on_log_created(self, log_path):
        self._log_path = log_path
        self._update_open_buttons()

    def _on_failed(self, message):
        self._failed = True
        self.statusbar.showMessage("Scan stopped: " + message.splitlines()[0])
        QMessageBox.warning(self, "PAnalizer", message)

    def _on_finished(self, analyzed, matches):
        worker = self._worker
        self._set_ui_running(False)
        self._worker = None
        if self.progressBar.maximum() == 0:
            self.progressBar.setRange(0, 1)
        if self._failed:
            state = "Did not complete"
        elif worker is not None and worker.stopped:
            state = "Stopped"
        else:
            state = "Finished"
        self.progressLabel.setText(f"{state} · {analyzed:,} images · {self._matches_text()}")

    def OnStopButtonClick(self):
        if self._worker is not None:
            self._worker.stop()
            self.StopButton.setEnabled(False)
            self.progressLabel.setText("Stopping after the current image…")

    # ── Results ──

    def _update_open_buttons(self):
        has_results = os.path.isdir(self.DirectoryResult.text().strip())
        has_log = bool(self._log_path) and os.path.isfile(self._log_path)
        for widget in (self.OpenResultsButton, self.actionOpenResults):
            widget.setEnabled(has_results)
        for widget in (self.OpenLogButton, self.actionOpenLog):
            widget.setEnabled(has_log)

    def _open(self, path):
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            QMessageBox.information(self, "PAnalizer", f"Could not open:\n{path}")

    def OpenResultsFolder(self):
        path = self.DirectoryResult.text().strip()
        if os.path.isdir(path):
            self._open(path)

    def OpenLog(self):
        if self._log_path:
            self._open(self._log_path)

    # ── Actions ──

    def OnNudeSearchButtonClick(self):
        paths = self._validate_paths()
        if paths:
            self._start(NudityWorker(paths["search"], paths["result"]), "Starting nudity screening…")

    def OnFaceSearchButtonClick(self):
        paths = self._validate_paths(require_learn=True)
        if paths:
            self._start(FaceWorker(paths["search"], paths["learn"], paths["result"]), "Starting face search…")

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(5000)
        event.accept()
