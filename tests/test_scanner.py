"""Unit tests for Libs/ImageScanner.py using fake models."""

import json
import os

import cv2
import numpy as np
import pytest

from Libs import ImageScanner


class FakeNudeDetector:
    def __init__(self, detections):
        self.detections = detections

    def detect(self, image):
        return self.detections


def _det(cls, score):
    return {"class": cls, "score": score, "box": [1, 2, 3, 4]}


@pytest.mark.parametrize(
    ("detections", "expected"),
    [
        ([_det("FEMALE_GENITALIA_EXPOSED", 0.9)], True),
        ([_det("MALE_GENITALIA_EXPOSED", 0.6)], True),        # threshold is inclusive
        ([_det("BUTTOCKS_EXPOSED", 0.59)], False),            # below threshold
        ([_det("FEMALE_BREAST_COVERED", 0.99)], False),       # covered: not explicit
        ([_det("FACE_FEMALE", 0.99), _det("ANUS_EXPOSED", 0.7)], True),
        ([], False),
    ],
)
def test_scan_nudity_rule(detections, expected):
    is_explicit, reported = ImageScanner.ScanNudity(None, threshold=0.6, detector=FakeNudeDetector(detections))
    assert is_explicit is expected
    assert [d["class"] for d in reported] == [d["class"] for d in detections]


def _face(x, y, w, h, score=0.95):
    row = np.zeros(15, dtype=np.float32)
    row[:4] = (x, y, w, h)
    row[14] = score
    return row


class FakeFaceModels:
    """faces_by_shape: image height -> list of face rows; features are the face x coordinate."""

    def __init__(self, faces_by_height, similarity, scale=1.0):
        self.faces_by_height = faces_by_height
        self.similarity = similarity
        self.scale = scale

    def DetectFaces(self, image):
        faces = self.faces_by_height.get(image.shape[0], [])
        return image, np.array(faces, dtype=np.float32).reshape(-1, 15), self.scale

    def Feature(self, image, face):
        return float(face[0])

    def Similarity(self, a, b):
        return self.similarity[(a, b)]


def test_recognize_matches_if_any_face_is_close_enough():
    models = FakeFaceModels({10: [_face(1, 0, 5, 5), _face(2, 0, 5, 5)]}, {(1.0, "ref"): 0.1, (2.0, "ref"): 0.5})
    found, faces = ImageScanner.RecognizeFaces(np.zeros((10, 10, 3)), ["ref"], models, threshold=0.363)
    assert found is True
    assert [f["match"] for f in faces] == [False, True]
    assert [f["similarity"] for f in faces] == [0.1, 0.5]


def test_recognize_uses_best_reference_and_maps_boxes_to_original_size():
    sims = {(10.0, "a"): 0.2, (10.0, "b"): 0.4}
    models = FakeFaceModels({10: [_face(10, 20, 30, 40)]}, sims, scale=0.5)
    found, faces = ImageScanner.RecognizeFaces(np.zeros((10, 10, 3)), ["a", "b"], models, threshold=0.363)
    assert found is True
    assert faces == [{"box": [20, 40, 60, 80], "similarity": 0.4, "match": True}]


def test_build_encodings_uses_best_face_and_skips_faceless_images(tmp_path):
    cv2.imwrite(str(tmp_path / "two_faces.png"), np.zeros((10, 10, 3), dtype=np.uint8))
    cv2.imwrite(str(tmp_path / "no_face.png"), np.zeros((20, 20, 3), dtype=np.uint8))
    (tmp_path / "notes.txt").write_text("not an image")
    (tmp_path / "sub").mkdir()
    cv2.imwrite(str(tmp_path / "sub" / "ignored.png"), np.zeros((10, 10, 3), dtype=np.uint8))
    models = FakeFaceModels({10: [_face(1, 0, 5, 5, score=0.8), _face(2, 0, 5, 5, score=0.99)]}, {})

    features, used = ImageScanner.BuildFaceEncodings(str(tmp_path), models)

    assert features == [2.0]
    assert used == [str(tmp_path / "two_faces.png")]


def test_read_image_handles_non_ascii_paths_and_bad_files(tmp_path):
    folder = tmp_path / "evidencia_ñandú"
    folder.mkdir()
    ok, encoded = cv2.imencode(".png", np.full((4, 4, 3), 7, dtype=np.uint8))
    (folder / "foto_año.png").write_bytes(encoded.tobytes())
    (folder / "broken.jpg").write_bytes(b"not a jpeg")

    assert ImageScanner.ReadImage(str(folder / "foto_año.png")).shape == (4, 4, 3)
    assert ImageScanner.ReadImage(str(folder / "broken.jpg")) is None
    assert ImageScanner.ReadImage(str(folder / "missing.png")) is None


def test_collect_image_files(tmp_path):
    (tmp_path / "a.JPG").write_bytes(b"")
    (tmp_path / "b.txt").write_bytes(b"")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.webp").write_bytes(b"")

    assert ImageScanner.CollectImageFiles(str(tmp_path)) == [str(tmp_path / "a.JPG"), str(tmp_path / "sub" / "c.webp")]
    assert ImageScanner.CollectImageFiles(str(tmp_path), recursive=False) == [str(tmp_path / "a.JPG")]


def test_copy_to_results_never_overwrites_and_keeps_timestamps(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    sources = []
    for i, folder in enumerate(("one", "two", "three")):
        (tmp_path / folder).mkdir()
        src = tmp_path / folder / "img.jpg"
        src.write_bytes(bytes([i]))
        os.utime(src, (1_000_000_000 + i, 1_000_000_000 + i))
        sources.append(src)

    copies = [ImageScanner.CopyToResults(str(s), str(results)) for s in sources]

    assert [os.path.basename(c) for c in copies] == ["img.jpg", "img_1.jpg", "img_2.jpg"]
    for i, c in enumerate(copies):
        assert open(c, "rb").read() == bytes([i])
        assert int(os.path.getmtime(c)) == 1_000_000_000 + i


def test_session_log_is_json_lines(tmp_path):
    log = ImageScanner.CreateSessionLog(str(tmp_path), "face", {"threshold": 0.363})
    ImageScanner.AppendToLog(log, ImageScanner.MakeLogEntry("a.jpg", True, {"faces": []}, copied_to="r/a.jpg"))
    ImageScanner.AppendToLog(log, ImageScanner.MakeLogEntry("b.jpg", False, error="could not decode image"))

    lines = [json.loads(line) for line in open(log, encoding="utf-8")]
    assert os.path.basename(log).startswith("panalizer_face_") and log.endswith(".jsonl")
    assert lines[0]["event"] == "session_start" and lines[0]["settings"] == {"threshold": 0.363}
    assert lines[1]["file"] == "a.jpg" and lines[1]["match"] is True and lines[1]["copied_to"] == "r/a.jpg"
    assert lines[2]["error"] == "could not decode image" and "copied_to" not in lines[2]
