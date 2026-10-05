"""Download the OpenCV face models used by Face Search into models/.

Each file is verified against a pinned SHA-256 hash. Files that are already
present with the correct hash are not downloaded again.

For offline machines, download the files listed in MODELS on a connected
machine, copy them into the models/ folder, and run this script to verify
them.

The models come from the OpenCV Model Zoo (https://github.com/opencv/opencv_zoo):
- YuNet face detector: MIT License
- SFace face recognizer: Apache License 2.0
"""

import hashlib
import os
import sys
import urllib.request

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models/"

MODELS = [
    (
        "face_detection_yunet_2023mar.onnx",
        ZOO + "face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    (
        "face_recognition_sface_2021dec.onnx",
        ZOO + "face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    ),
]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(name, url, expected_hash):
    path = os.path.join(MODELS_DIR, name)
    if os.path.isfile(path):
        if sha256(path) == expected_hash:
            print(f"OK          {name}")
            return True
        print(f"BAD HASH    {name}: re-downloading")

    print(f"Downloading {name} ...")
    tmp_path = path + ".part"
    try:
        with urllib.request.urlopen(url, timeout=60) as response, open(tmp_path, "wb") as out:
            for chunk in iter(lambda: response.read(1 << 20), b""):
                out.write(chunk)
    except OSError as e:
        print(f"FAILED      {name}: {e}\n            Download it manually from {url}")
        return False

    actual_hash = sha256(tmp_path)
    if actual_hash != expected_hash:
        os.remove(tmp_path)
        print(f"FAILED      {name}: SHA-256 mismatch (got {actual_hash})")
        return False
    os.replace(tmp_path, path)
    print(f"OK          {name}")
    return True


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    results = [fetch(name, url, digest) for name, url, digest in MODELS]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
