"""Smoke tests: no GPU, no network, no images on disk.

They check that the modules import, the bundled Haar cascades load, the
OpenCV APIs used by the scanner exist in the installed version, and the
main window can be constructed.
"""

import os

import cv2
import numpy as np
import pytest

from Libs import ImageScanner

CASCADES = [
    "haarcascade_frontalface_default.xml",
    "haarcascade_frontalface_alt.xml",
    "haarcascade_frontalface_alt2.xml",
    "haarcascade_frontalface_alt_tree.xml",
    "haarcascade_profileface.xml",
]


@pytest.mark.parametrize("name", CASCADES)
def test_bundled_cascade_loads(name):
    path = os.path.join(os.path.dirname(ImageScanner.__file__), name)
    assert not cv2.CascadeClassifier(path).empty()


def test_lbph_recognizer_available():
    # Face search needs cv2.face, which only opencv-contrib-python provides.
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces = [np.full((64, 64), v, dtype=np.uint8) for v in (10, 20, 30)]
    recognizer.train(faces, np.array([1, 1, 1]))
    label, _distance = recognizer.predict(faces[0])
    assert label == 1


def test_face_search_on_blank_image_finds_nothing():
    blank = np.zeros((240, 320, 3), dtype=np.uint8)
    assert ImageScanner.FaceSearchForRecognize(blank) == ([], [])
    assert ImageScanner.FaceSearchForTrainig(blank) == (None, None)


def test_body_search_on_blank_image_finds_nothing():
    blank = np.zeros((240, 320, 3), dtype=np.uint8)
    assert len(ImageScanner.BodySearch(blank)) == 0


def test_skin_scan_thresholds():
    skin = np.zeros((20, 20, 3), dtype=np.uint8)
    skin[:] = (100, 150, 220)  # BGR, inside the HSV skin range
    black = np.zeros((20, 20, 3), dtype=np.uint8)
    assert ImageScanner.SkinScan(skin) is True
    assert ImageScanner.SkinScan(black) is False


def test_main_window_constructs():
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from ViewModels.PAnalizerViewModel import MainWindow

    window = MainWindow()
    assert window.FaceSearchButton.text() == "Face Search"
    assert window.NudeSearchButton.text() == "Nude Search"
    window.close()
    assert app is not None


def test_entry_point_imports():
    import PAnalizer  # noqa: F401  (guarded by __main__, so nothing starts)
