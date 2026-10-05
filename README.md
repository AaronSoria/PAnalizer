# PAnalizer

[![CI](https://github.com/AaronSoria/PAnalizer/actions/workflows/ci.yml/badge.svg)](https://github.com/AaronSoria/PAnalizer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

PAnalizer is a desktop digital-forensics tool for triaging large image sets.
It helps an investigator:

- **Flag images that may contain nudity**, so they can be prioritized for
  manual review.
- **Search for a person of interest** across a folder of images, given a few
  reference photos of that person.

Matching images are listed in the application and copied to a results folder.
PAnalizer is a triage aid: every result must be reviewed by a person.

## Features

- **Nudity screening (heuristic).** For each image, OpenCV's HOG people
  detector locates human figures, `grabCut` separates each figure from the
  background, and the image is flagged when the share of skin-colored pixels
  (HSV range) in a figure exceeds 1%. No machine-learning nudity model is used.
- **Person-of-interest search.** Faces in the reference photos are found with
  OpenCV Haar cascades (frontal and profile) and used to train an LBPH face
  recognizer. Faces found in the searched images are compared against it and
  reported as a match when the LBPH distance is below 50.
- **Recursive search** of the selected folder and its subfolders. Any image
  format OpenCV can read is processed; other files are skipped.
- **Runs fully offline.** No images or results leave the machine.
- Simple Qt (PyQt5) graphical interface on Windows and Linux.

## Requirements

- Python **3.11 or newer** (tested on 3.11 and 3.13)
- Windows or Linux with a graphical desktop
- Python packages (pinned in [`requirements.txt`](requirements.txt)):
  `opencv-contrib-python`, `numpy`, `imutils`, `PyQt5`

No GPU and no model downloads are needed; the Haar cascade files ship with the
repository in `Libs/`.

## Installation

Using a virtual environment is recommended. No administrator rights are needed.

### Linux

```bash
git clone https://github.com/AaronSoria/PAnalizer.git
cd PAnalizer
python3 -m venv .venv
. .venv/bin/activate
python install_linux.py        # same as: pip install -r requirements.txt
```

On minimal installations OpenCV and Qt may need extra system libraries. On
Debian/Ubuntu:

```bash
sudo apt-get install libgl1 libglib2.0-0 libegl1 libxkbcommon0 libfontconfig1
```

### Windows

```bat
git clone https://github.com/AaronSoria/PAnalizer.git
cd PAnalizer
py -3 -m venv .venv
.venv\Scripts\activate
python install_windows.py
```

> Install **only** `opencv-contrib-python`. Having `opencv-python` installed
> in the same environment conflicts with it; uninstall it if present.

## Usage

```bash
python PAnalizer.py
```

The window has three folder fields; use the **Search** button next to each to
pick a folder.

| Field | Used by | Purpose |
|---|---|---|
| Directory for searching | both | Images to analyze (subfolders included) |
| Directory for learning | Face Search | Reference photos of the person of interest |
| Directory for results | both | Where matching images are copied |

- **Nude Search**: fill in the search and results folders, then click
  **Nude Search**.
- **Face Search**: also fill in the learning folder. Use several clear photos
  where the person's face is visible; only the first face detected in each
  reference photo is used, and subfolders of the learning folder are not read.

The search and results folders must be different. Paths of matching images
appear in the text area at the bottom of the window.

## Project structure

```
PAnalizer.py                    Entry point: starts the Qt application
ViewModels/PAnalizerViewModel.py  Main window logic: folder selection, scanning, copying results
Views/PAnalizerView.ui          Qt Designer layout
Views/PAnalizerView_ui.py       Python code generated from the .ui file (pyuic5)
Libs/ImageScanner.py            Detection: body/skin heuristic, face detection and recognition
Libs/haarcascade_*.xml          OpenCV Haar cascade models for face detection
install_linux.py, install_windows.py  Dependency installers
tests/                          Smoke tests (no GPU or images required)
```

## Limitations

Read these before relying on any result.

- **Nudity screening is a color heuristic, not a trained classifier.** Expect
  many false positives (any figure with a little visible skin, skin-toned
  backgrounds) and false negatives (figures the people detector misses,
  lighting or skin tones outside the fixed HSV range). Accuracy has not been
  measured; validate on your own data.
- **Face recognition uses LBPH**, a classical method that is sensitive to
  pose, lighting, resolution and occlusion. The match threshold (50) is fixed
  in the code.
- **The interface is unresponsive during a scan**, and the progress bar does
  not advance. Large folders can take a long time.
- **Results are copied into a single flat folder**: files with the same name
  from different subfolders overwrite each other. Copies do not preserve file
  timestamps, and no hashes or logs are produced, so PAnalizer does not by
  itself provide evidence integrity or chain of custody. Work on a forensic
  copy of the data, never on the original evidence.
- **Known bugs**: Face Search writes copies next to the results folder (the
  folder path and file name are joined without a separator); only the first
  face found in each searched image is compared; and if no face is detected
  in any reference photo, Face Search stops with an OpenCV error.

## Responsible use

PAnalizer is intended for lawful forensic and investigative work, such as
law-enforcement or corporate investigations and content-moderation triage,
carried out by authorized people.

- Use it only on data you are legally authorized to examine, and follow the
  laws and procedures of your jurisdiction, including privacy and
  data-protection law.
- Do not use it to surveil, identify or track people without a legal basis.
- Automated results are leads, not conclusions. Have every match confirmed
  by a qualified person before acting on it.
- If you encounter child sexual abuse material, do not copy or share it;
  report it to the competent authorities (for example NCMEC or your national
  hotline listed by INHOPE).

## License

[MIT](LICENSE) © 2019 Aaron Soria

## Contributing

Bug reports and pull requests are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the development setup, and never attach
explicit images to issues.
