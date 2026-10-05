"""Image analysis for PAnalizer.

- Nudity screening: NudeNet 3.x detector (ONNX model bundled with the
  ``nudenet`` package).
- Person-of-interest search: OpenCV YuNet face detector + SFace face
  recognizer (ONNX models in ``models/``, fetched by ``download_models.py``).
"""

import datetime
import json
import os
import shutil

import cv2
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
YUNET_MODEL = "face_detection_yunet_2023mar.onnx"
SFACE_MODEL = "face_recognition_sface_2021dec.onnx"

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")

# NudeNet 3.x labels treated as explicit content.
EXPLICIT_CLASSES = frozenset({
    "ANUS_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
})

DEFAULT_NUDITY_THRESHOLD = 0.6
# Cosine-similarity threshold recommended for SFace in OpenCV's
# samples/dnn/face_detect.py (same person if similarity >= 0.363).
DEFAULT_FACE_THRESHOLD = 0.363
# YuNet runs on images downscaled so their longest side is at most this.
MAX_DETECTION_SIDE = 1280


class ModelNotFoundError(FileNotFoundError):
    pass


# ──────────────────────────────────────────────
# Image I/O
# ──────────────────────────────────────────────

def ReadImage(image_path):
    """Read an image as a BGR array, or return None if it cannot be decoded.

    Uses np.fromfile + cv2.imdecode so non-ASCII paths work on Windows.
    """
    try:
        data = np.fromfile(image_path, dtype=np.uint8)
    except OSError:
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def CollectImageFiles(directory, recursive=True):
    """Return the paths of supported image files in directory, sorted."""
    image_files = []
    if recursive:
        for base, _, files in os.walk(directory):
            for filename in files:
                if filename.lower().endswith(SUPPORTED_EXTENSIONS):
                    image_files.append(os.path.join(base, filename))
    else:
        for filename in os.listdir(directory):
            full_path = os.path.join(directory, filename)
            if os.path.isfile(full_path) and filename.lower().endswith(SUPPORTED_EXTENSIONS):
                image_files.append(full_path)
    return sorted(image_files)


# ──────────────────────────────────────────────
# Nudity screening — NudeNet
# ──────────────────────────────────────────────

_nude_detector = None


def LoadNudityDetector():
    """Return the shared NudeNet detector, loading it on first use."""
    global _nude_detector
    if _nude_detector is None:
        from nudenet import NudeDetector
        _nude_detector = NudeDetector()
    return _nude_detector


def ScanNudity(image, threshold=DEFAULT_NUDITY_THRESHOLD, detector=None):
    """Run NudeNet on a BGR image.

    Returns (is_explicit, detections), where detections is the list of
    {"class", "score", "box"} dicts reported by NudeNet. The image is
    explicit if any EXPLICIT_CLASSES detection scores >= threshold.
    """
    detector = detector or LoadNudityDetector()
    detections = [
        {"class": d["class"], "score": round(float(d["score"]), 4), "box": [int(v) for v in d["box"]]}
        for d in detector.detect(image)
    ]
    is_explicit = any(d["class"] in EXPLICIT_CLASSES and d["score"] >= threshold for d in detections)
    return is_explicit, detections


# ──────────────────────────────────────────────
# Person-of-interest search — OpenCV YuNet + SFace
# ──────────────────────────────────────────────

def _model_path(models_dir, name):
    path = os.path.join(models_dir, name)
    if not os.path.isfile(path):
        raise ModelNotFoundError(
            f"Face model not found: {path}\n"
            "Run 'python download_models.py' to download it."
        )
    return path


class FaceModels:
    """YuNet face detector and SFace recognizer."""

    def __init__(self, models_dir=MODELS_DIR, score_threshold=0.9):
        self.detector = cv2.FaceDetectorYN.create(
            _model_path(models_dir, YUNET_MODEL), "", (320, 320), score_threshold, 0.3, 5000
        )
        self.recognizer = cv2.FaceRecognizerSF.create(_model_path(models_dir, SFACE_MODEL), "")

    def DetectFaces(self, image):
        """Return (resized_image, faces, scale).

        faces is an (N, 15) array of YuNet detections on resized_image;
        divide box coordinates by scale to map them to the original image.
        """
        height, width = image.shape[:2]
        scale = min(1.0, MAX_DETECTION_SIDE / max(height, width))
        if scale < 1.0:
            image = cv2.resize(image, (round(width * scale), round(height * scale)))
        self.detector.setInputSize((image.shape[1], image.shape[0]))
        _, faces = self.detector.detect(image)
        if faces is None:
            faces = np.empty((0, 15), dtype=np.float32)
        return image, faces, scale

    def Feature(self, image, face):
        return self.recognizer.feature(self.recognizer.alignCrop(image, face))

    def Similarity(self, feature_a, feature_b):
        return float(self.recognizer.match(feature_a, feature_b, cv2.FaceRecognizerSF_FR_COSINE))


def BuildFaceEncodings(reference_directory, models):
    """Return (features, used_files) for the reference photos.

    Uses the highest-scoring face in each supported image directly inside
    reference_directory (subfolders are not read). Images without a
    detectable face are skipped.
    """
    features, used_files = [], []
    for path in CollectImageFiles(reference_directory, recursive=False):
        image = ReadImage(path)
        if image is None:
            continue
        resized, faces, _ = models.DetectFaces(image)
        if len(faces) == 0:
            continue
        best = faces[np.argmax(faces[:, 14])]
        features.append(models.Feature(resized, best))
        used_files.append(path)
    return features, used_files


def RecognizeFaces(image, reference_features, models, threshold=DEFAULT_FACE_THRESHOLD):
    """Compare every face in a BGR image against the reference features.

    Returns (found, faces) where faces is a list of
    {"box": [x, y, w, h], "similarity": float, "match": bool}, with boxes
    in original-image coordinates and similarity being the best cosine
    similarity against any reference face.
    """
    resized, detections, scale = models.DetectFaces(image)
    faces = []
    for face in detections:
        feature = models.Feature(resized, face)
        similarity = max((models.Similarity(feature, ref) for ref in reference_features), default=0.0)
        faces.append({
            "box": [int(round(v / scale)) for v in face[:4]],
            "similarity": round(similarity, 4),
            "match": similarity >= threshold,
        })
    return any(f["match"] for f in faces), faces


# ──────────────────────────────────────────────
# Results: copies and session log (JSON Lines)
# ──────────────────────────────────────────────

def CopyToResults(source_path, result_directory):
    """Copy source_path into result_directory without overwriting.

    Keeps file timestamps (shutil.copy2). If a file with the same name
    already exists, appends _1, _2, ... before the extension.
    Returns the destination path.
    """
    name, ext = os.path.splitext(os.path.basename(source_path))
    destination = os.path.join(result_directory, name + ext)
    counter = 1
    while os.path.exists(destination):
        destination = os.path.join(result_directory, f"{name}_{counter}{ext}")
        counter += 1
    shutil.copy2(source_path, destination)
    return destination


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def CreateSessionLog(result_directory, scan_type, settings):
    """Create a JSON Lines log in result_directory and return its path.

    The first line describes the session; AppendToLog adds one line per
    analyzed file.
    """
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(result_directory, f"panalizer_{scan_type}_{stamp}.jsonl")
    header = {"event": "session_start", "timestamp": _now(), "scan_type": scan_type, "settings": settings}
    with open(log_path, "x", encoding="utf-8") as f:
        f.write(json.dumps(header, ensure_ascii=False) + "\n")
    return log_path


def AppendToLog(log_path, entry):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def MakeLogEntry(image_path, is_match, details=None, copied_to=None, error=None):
    entry = {
        "event": "result",
        "timestamp": _now(),
        "file": image_path,
        "match": is_match,
        "details": details or {},
    }
    if copied_to:
        entry["copied_to"] = copied_to
    if error:
        entry["error"] = error
    return entry
