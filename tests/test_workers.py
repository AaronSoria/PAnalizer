"""End-to-end tests for the scan workers, run synchronously with fake models."""

import json
import os

import cv2
import numpy as np
import pytest
from PyQt5 import QtWidgets

from Libs import ImageScanner
from ViewModels import PAnalizerViewModel


@pytest.fixture(autouse=True)
def qt_app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _record(worker):
    events = {"failed": [], "finished": [], "found": []}
    worker.failed.connect(events["failed"].append)
    worker.scan_finished.connect(lambda analyzed, matches: events["finished"].append((analyzed, matches)))
    worker.result_found.connect(events["found"].append)
    return events


def _image(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.full((8, 8, 3), value, dtype=np.uint8))


def _log_lines(results):
    (log,) = [f for f in os.listdir(results) if f.endswith(".jsonl")]
    return [json.loads(line) for line in open(os.path.join(results, log), encoding="utf-8")]


class ValueDetector:
    """Flags images whose pixel value is 200 as explicit."""

    def detect(self, image):
        if int(image[0, 0, 0]) == 200:
            return [{"class": "FEMALE_GENITALIA_EXPOSED", "score": 0.9, "box": [0, 0, 8, 8]}]
        return []


def test_nudity_worker_end_to_end(tmp_path, monkeypatch):
    search, results = tmp_path / "search", tmp_path / "results"
    results.mkdir()
    _image(search / "a" / "img.png", 200)
    _image(search / "b" / "img.png", 200)    # same name, must not overwrite
    _image(search / "safe.png", 10)
    (search / "corrupt.jpg").write_bytes(b"garbage")
    monkeypatch.setattr(PAnalizerViewModel, "LoadNudityDetector", ValueDetector)

    worker = PAnalizerViewModel.NudityWorker(str(search), str(results))
    events = _record(worker)
    worker.run()

    assert events["failed"] == []
    assert events["finished"] == [(4, 2)]
    assert len(events["found"]) == 2
    assert sorted(f for f in os.listdir(results) if f.endswith(".png")) == ["img.png", "img_1.png"]
    lines = _log_lines(results)
    assert lines[0]["scan_type"] == "nudity" and lines[0]["settings"]["threshold"] == 0.6
    by_file = {os.path.basename(e["file"]): e for e in lines[1:]}
    assert by_file["corrupt.jpg"]["error"] == "could not decode image"
    assert by_file["safe.png"]["match"] is False


def test_face_worker_reports_missing_models_and_still_finishes(tmp_path, monkeypatch):
    for d in ("search", "learn", "results"):
        (tmp_path / d).mkdir()

    def missing():
        raise ImageScanner.ModelNotFoundError("Face model not found\nRun 'python download_models.py'")

    monkeypatch.setattr(PAnalizerViewModel, "FaceModels", missing)
    worker = PAnalizerViewModel.FaceWorker(*(str(tmp_path / d) for d in ("search", "learn", "results")))
    events = _record(worker)
    worker.run()

    assert len(events["failed"]) == 1 and "download_models.py" in events["failed"][0]
    assert events["finished"] == [(0, 0)]


def test_face_worker_without_reference_faces_fails_cleanly(tmp_path, monkeypatch):
    for d in ("search", "learn", "results"):
        (tmp_path / d).mkdir()
    _image(tmp_path / "search" / "x.png", 1)
    monkeypatch.setattr(PAnalizerViewModel, "FaceModels", lambda: object())
    monkeypatch.setattr(PAnalizerViewModel, "BuildFaceEncodings", lambda path, models: ([], []))

    worker = PAnalizerViewModel.FaceWorker(*(str(tmp_path / d) for d in ("search", "learn", "results")))
    events = _record(worker)
    worker.run()

    assert "No face was detected" in events["failed"][0]
    assert events["finished"] == [(0, 0)]
    assert os.listdir(tmp_path / "results") == []


def test_face_worker_end_to_end(tmp_path, monkeypatch):
    search, results = tmp_path / "search", tmp_path / "results"
    results.mkdir()
    _image(search / "match.png", 1)
    _image(search / "other.png", 2)
    monkeypatch.setattr(PAnalizerViewModel, "FaceModels", lambda: object())
    monkeypatch.setattr(PAnalizerViewModel, "BuildFaceEncodings", lambda path, models: (["ref"], ["r.jpg"]))

    def recognize(image, refs, models, threshold):
        hit = int(image[0, 0, 0]) == 1
        return hit, [{"box": [0, 0, 8, 8], "similarity": 0.9 if hit else 0.1, "match": hit}]

    monkeypatch.setattr(PAnalizerViewModel, "RecognizeFaces", recognize)
    worker = PAnalizerViewModel.FaceWorker(str(search), str(tmp_path), str(results))
    events = _record(worker)
    worker.run()

    assert events["failed"] == []
    assert events["finished"] == [(2, 1)]
    assert "match.png" in os.listdir(results) and "other.png" not in os.listdir(results)
    assert _log_lines(results)[0]["settings"]["reference_files"] == ["r.jpg"]
