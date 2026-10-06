"""Smoke tests: modules import, models load, the main window builds."""

import os

import numpy as np
import pytest

from Libs import ImageScanner

HAVE_FACE_MODELS = all(
    os.path.isfile(os.path.join(ImageScanner.MODELS_DIR, name))
    for name in (ImageScanner.YUNET_MODEL, ImageScanner.SFACE_MODEL)
)
needs_face_models = pytest.mark.skipif(not HAVE_FACE_MODELS, reason="run download_models.py first")


def test_nudenet_loads_and_blank_image_is_safe():
    assert ImageScanner.ScanNudity(np.zeros((240, 320, 3), dtype=np.uint8)) == (False, [])


@needs_face_models
def test_face_models_load_and_blank_image_has_no_faces():
    models = ImageScanner.FaceModels()
    assert ImageScanner.RecognizeFaces(np.zeros((240, 320, 3), dtype=np.uint8), [], models) == (False, [])


@needs_face_models
def test_large_images_are_downscaled_for_detection():
    models = ImageScanner.FaceModels()
    resized, faces, scale = models.DetectFaces(np.zeros((3000, 4000, 3), dtype=np.uint8))
    assert max(resized.shape[:2]) == ImageScanner.MAX_DETECTION_SIDE
    assert scale == pytest.approx(0.32)
    assert faces.shape == (0, 15)


def test_missing_face_models_raise_helpful_error(tmp_path):
    with pytest.raises(ImageScanner.ModelNotFoundError, match="download_models.py"):
        ImageScanner.FaceModels(models_dir=str(tmp_path))


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


@needs_face_models
def test_face_detector_uses_default_confidence(monkeypatch):
    created = []
    real_create = ImageScanner.cv2.FaceDetectorYN.create
    monkeypatch.setattr(ImageScanner.cv2.FaceDetectorYN, "create",
                        lambda *args: created.append(args) or real_create(*args))
    ImageScanner.FaceModels()
    assert ImageScanner.DEFAULT_DETECTION_SCORE == 0.7
    assert created[0][3] == ImageScanner.DEFAULT_DETECTION_SCORE
