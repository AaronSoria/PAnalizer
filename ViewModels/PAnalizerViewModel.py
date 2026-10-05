# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2026 Aaron Soria

import os

from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from Libs.ImageScanner import (
    DEFAULT_FACE_THRESHOLD,
    DEFAULT_NUDITY_THRESHOLD,
    AppendToLog,
    BuildFaceEncodings,
    CollectImageFiles,
    CopyToResults,
    CreateSessionLog,
    FaceModels,
    LoadNudityDetector,
    MakeLogEntry,
    ReadImage,
    RecognizeFaces,
    ScanNudity,
)
from Views.PAnalizerView_ui import Ui_MainWindow


# ──────────────────────────────────────────────
# Workers — run in a background thread so the UI stays responsive
# ──────────────────────────────────────────────

class ScanWorker(QThread):
    progress = pyqtSignal(int)              # 0-100
    result_found = pyqtSignal(str)          # path of a matching file
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

    def stop(self):
        self._stop = True

    def settings(self):
        return {"search_directory": self.search_path}

    def prepare(self):
        """Load models before scanning. Raise to abort the scan."""

    def analyze(self, image):
        """Return (is_match, details) for a BGR image."""
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
        for i, file_path in enumerate(image_files):
            if self._stop:
                break
            self.status_message.emit(f"Analyzing ({i + 1}/{total}): {os.path.basename(file_path)}")
            AppendToLog(log_path, self._process(file_path))
            self._analyzed += 1
            self.progress.emit(int((i + 1) / total * 100))

        stopped = " (stopped)" if self._stop else ""
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
            self.result_found.emit(file_path)
            try:
                copied_to = CopyToResults(file_path, self.result_path)
            except OSError as e:
                error = f"copy failed: {e}"
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
            "reference_directory": self.learn_path,
            "reference_files": self.reference_files,
        }

    def prepare(self):
        self.status_message.emit("Loading face models and reference photos...")
        self.models = FaceModels()
        self.reference_features, self.reference_files = BuildFaceEncodings(self.learn_path, self.models)
        if not self.reference_features:
            raise RuntimeError(
                "No face was detected in the photos of the learning directory. "
                "Add clear photos of the person's face and try again."
            )
        self.status_message.emit(f"{len(self.reference_features)} reference face(s) loaded. Searching...")

    def analyze(self, image):
        found, faces = RecognizeFaces(image, self.reference_features, self.models, threshold=self.threshold)
        return found, {"faces": faces}


# ──────────────────────────────────────────────
# Main window
# ──────────────────────────────────────────────

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle("PAnalizer")
        self._worker = None

        self.SearchDirectoryButton.clicked.connect(self.OnSearchDirectoryButtonClick)
        self.SearchLearnButton.clicked.connect(self.OnSearchLearnButtonClick)
        self.SearchResultButton.clicked.connect(self.OnLearnResultButtonClick)
        self.FaceSearchButton.clicked.connect(self.OnFaceSearchButtonClick)
        self.NudeSearchButton.clicked.connect(self.OnNudeSearchButtonClick)

    # ── Folder selection ──

    def OnSearchDirectoryButtonClick(self):
        d = QFileDialog.getExistingDirectory(self, "Directory for searching")
        if d:
            self.DirectorySearch.setPlainText(d)

    def OnSearchLearnButtonClick(self):
        d = QFileDialog.getExistingDirectory(self, "Directory for learning (photos of the person)")
        if d:
            self.DirectoryLearn.setPlainText(d)

    def OnLearnResultButtonClick(self):
        d = QFileDialog.getExistingDirectory(self, "Directory for results")
        if d:
            self.DirectoryResult.setPlainText(d)

    # ── Validation ──

    def _validate_paths(self, require_learn=False):
        search = self.DirectorySearch.toPlainText().strip()
        result = self.DirectoryResult.toPlainText().strip()
        learn = self.DirectoryLearn.toPlainText().strip()

        error = None
        if not os.path.isdir(search):
            error = "The directory for searching is not valid."
        elif not os.path.isdir(result):
            error = "The directory for results is not valid."
        elif os.path.normcase(os.path.abspath(search)) == os.path.normcase(os.path.abspath(result)):
            error = "The directories for searching and results must be different."
        elif require_learn and not os.path.isdir(learn):
            error = "The directory for learning is not valid."
        if error:
            QMessageBox.warning(self, "PAnalizer", error)
            return None
        return {"search": search, "result": result, "learn": learn}

    # ── Worker lifecycle ──

    def _set_ui_running(self, running):
        for widget in (self.FaceSearchButton, self.NudeSearchButton, self.SearchDirectoryButton,
                       self.SearchLearnButton, self.SearchResultButton):
            widget.setEnabled(not running)

    def _start(self, worker, message):
        self.ShowResultText.clear()
        self.progressBar.setValue(0)
        self._set_ui_running(True)
        self.statusbar.showMessage(message)
        self._worker = worker
        worker.progress.connect(self.progressBar.setValue)
        worker.result_found.connect(self.ShowResultText.appendPlainText)
        worker.status_message.connect(self.statusbar.showMessage)
        worker.failed.connect(self._on_failed)
        worker.scan_finished.connect(self._on_finished)
        worker.start()

    def _on_failed(self, message):
        self.statusbar.showMessage("Scan stopped: " + message.splitlines()[0])
        QMessageBox.warning(self, "PAnalizer", message)

    def _on_finished(self, analyzed, matches):
        self._set_ui_running(False)
        self._worker = None

    # ── Actions ──

    def OnNudeSearchButtonClick(self):
        paths = self._validate_paths()
        if paths:
            self._start(NudityWorker(paths["search"], paths["result"]), "Starting nudity screening...")

    def OnFaceSearchButtonClick(self):
        paths = self._validate_paths(require_learn=True)
        if paths:
            self._start(FaceWorker(paths["search"], paths["learn"], paths["result"]), "Starting face search...")

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(5000)
        event.accept()
