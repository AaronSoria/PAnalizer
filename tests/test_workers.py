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
    worker.result_found.connect(lambda path, score, copied_to: events["found"].append((path, score, copied_to)))
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
    for path, score, copied_to in events["found"]:
        assert score == 0.9 and os.path.dirname(copied_to) == str(results)
    assert sorted(f for f in os.listdir(results) if f.endswith(".png")) == ["img.png", "img_1.png"]
    lines = _log_lines(results)
    assert lines[0]["scan_type"] == "nudity" and lines[0]["settings"]["threshold"] == 0.6
    by_file = {os.path.basename(e["file"]): e for e in lines[1:-1]}
    assert by_file["corrupt.jpg"]["error"] == "could not decode image"
    assert by_file["safe.png"]["match"] is False
    assert lines[-1] == {**lines[-1], "event": "session_end", "images_found": 4, "images_analyzed": 4,
                         "matches": 2, "stopped_by_user": False}


def test_face_worker_reports_missing_models_and_still_finishes(tmp_path, monkeypatch):
    for d in ("search", "learn", "results"):
        (tmp_path / d).mkdir()

    def missing(**kwargs):
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
    monkeypatch.setattr(PAnalizerViewModel, "FaceModels", lambda **kwargs: object())
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
    monkeypatch.setattr(PAnalizerViewModel, "FaceModels", lambda **kwargs: object())
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


def test_stopped_scan_is_recorded_in_log(tmp_path, monkeypatch):
    search, results = tmp_path / "search", tmp_path / "results"
    results.mkdir()
    for i in range(3):
        _image(search / f"img{i}.png", 10)

    class StopAfterFirst(ValueDetector):
        def __init__(self):
            self.worker = None

        def detect(self, image):
            self.worker.stop()
            return []

    detector = StopAfterFirst()
    monkeypatch.setattr(PAnalizerViewModel, "LoadNudityDetector", lambda: detector)
    worker = PAnalizerViewModel.NudityWorker(str(search), str(results))
    detector.worker = worker
    progress = []
    worker.progress.connect(lambda done, total: progress.append((done, total)))
    events = _record(worker)
    worker.run()

    assert worker.stopped is True
    assert events["finished"] == [(1, 0)]
    assert progress == [(0, 3), (1, 3)]
    end = _log_lines(results)[-1]
    assert end["event"] == "session_end" and end["stopped_by_user"] is True
    assert end["images_found"] == 3 and end["images_analyzed"] == 1


def test_face_worker_score_is_best_similarity():
    worker = PAnalizerViewModel.FaceWorker("s", "l", "r")
    assert worker.score({"faces": [{"similarity": 0.2}, {"similarity": 0.7}]}) == 0.7
    assert worker.score({"faces": []}) == 0.0


def test_face_worker_uses_and_logs_custom_thresholds(tmp_path, monkeypatch):
    search, results = tmp_path / "search", tmp_path / "results"
    results.mkdir()
    _image(search / "x.png", 1)
    created = []
    monkeypatch.setattr(PAnalizerViewModel, "FaceModels", lambda **kwargs: created.append(kwargs) or object())
    monkeypatch.setattr(PAnalizerViewModel, "BuildFaceEncodings", lambda path, models: (["ref"], ["r.jpg"]))
    used = []

    def recognize(image, refs, models, threshold):
        used.append(threshold)
        return False, []

    monkeypatch.setattr(PAnalizerViewModel, "RecognizeFaces", recognize)
    worker = PAnalizerViewModel.FaceWorker(str(search), str(tmp_path), str(results), threshold=0.5,
                                           detection_score=0.6)
    worker.run()

    assert created == [{"score_threshold": 0.6}] and used == [0.5]
    settings = _log_lines(results)[0]["settings"]
    assert (settings["threshold_cosine"], settings["detection_confidence"]) == (0.5, 0.6)
    assert settings["default_thresholds"] is False


def test_default_thresholds_are_flagged_in_log(tmp_path, monkeypatch):
    search, results = tmp_path / "search", tmp_path / "results"
    results.mkdir()
    _image(search / "x.png", 1)
    monkeypatch.setattr(PAnalizerViewModel, "LoadNudityDetector", ValueDetector)
    for threshold, expected in ((0.6, True), (0.8, False)):
        for f in results.iterdir():
            f.unlink()
        PAnalizerViewModel.NudityWorker(str(search), str(results), threshold=threshold).run()
        assert _log_lines(results)[0]["settings"]["default_thresholds"] is expected
