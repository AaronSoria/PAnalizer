"""Install PAnalizer's Python dependencies and face models on Linux.

Run with the Python interpreter you will use to start PAnalizer, ideally
inside a virtual environment (no sudo required):

    python3 -m venv .venv
    . .venv/bin/activate
    python install_linux.py
"""

import os
import subprocess
import sys

MIN_PYTHON = (3, 11)
HERE = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS = os.path.join(HERE, "requirements.txt")
DOWNLOAD_MODELS = os.path.join(HERE, "download_models.py")


def main():
    if sys.version_info < MIN_PYTHON:
        sys.exit("PAnalizer requires Python %d.%d or newer (found %s)."
                 % (MIN_PYTHON + (sys.version.split()[0],)))
    for cmd in ([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS],
                [sys.executable, DOWNLOAD_MODELS]):
        print(">>> " + " ".join(cmd))
        code = subprocess.call(cmd)
        if code != 0:
            sys.exit(code)


if __name__ == "__main__":
    main()
