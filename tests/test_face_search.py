"""Regression tests for Face Search. Recognition is stubbed: no real faces needed."""

import os

import cv2
import numpy as np
import pytest
from PyQt5 import QtWidgets

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
