"""Regression tests for Face Search. Recognition is stubbed: no real faces needed."""

import os

import cv2
import numpy as np
import pytest
from PyQt5 import QtWidgets

from Libs import ImageScanner
from ViewModels import PAnalizerViewModel


@pytest.fixture
def window():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w = PAnalizerViewModel.MainWindow()
    yield w
    w.close()
    assert app is not None


@pytest.fixture
def folders(tmp_path):
    search, learn, results = (tmp_path / n for n in ("search", "learn", "results"))
    for d in (search, learn, results):
        d.mkdir()
    cv2.imwrite(str(search / "photo.png"), np.zeros((32, 32, 3), dtype=np.uint8))
    return search, learn, results


def _fill(window, search, learn, results):
    window.DirectorySearch.setPlainText(str(search))
    window.DirectoryLearn.setPlainText(str(learn))
    window.DirectoryResult.setPlainText(str(results))


def test_face_search_copies_match_into_results_folder(window, folders, monkeypatch):
    search, learn, results = folders
    monkeypatch.setattr(PAnalizerViewModel, "TrainRecognizer", lambda path: object())
    monkeypatch.setattr(PAnalizerViewModel, "Recognize", lambda rec, img, dist: True)
    _fill(window, search, learn, results)

    window.OnFaceSearchButtonClick()

    assert os.listdir(results) == ["photo.png"]
    assert not os.path.exists(str(results) + "photo.png")


class _FakeRecognizer:
    """Returns the given LBPH distances, one per predict() call."""

    def __init__(self, distances):
        self._distances = iter(distances)

    def predict(self, face):
        return 1, next(self._distances)


@pytest.mark.parametrize(
    ("distances", "expected"),
    [
        ([90.0, 10.0], True),   # match is not the first face
        ([10.0, 90.0], True),
        ([90.0, 80.0], False),
        ([], False),            # no faces in the image
    ],
)
def test_recognize_checks_every_face(monkeypatch, distances, expected):
    faces = [np.zeros((8, 8), dtype=np.uint8) for _ in distances]
    monkeypatch.setattr(ImageScanner, "FaceSearchForRecognize", lambda image: (faces, [None] * len(faces)))

    assert ImageScanner.Recognize(_FakeRecognizer(distances), image=None, distance=50) is expected
