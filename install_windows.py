r"""Install PAnalizer's Python dependencies on Windows.

Run with the Python interpreter you will use to start PAnalizer, ideally
inside a virtual environment (no administrator rights required):

    py -3 -m venv .venv
    .venv\Scripts\activate
    python install_windows.py
"""

import os
import subprocess
import sys

MIN_PYTHON = (3, 11)
REQUIREMENTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")


def main():
    if sys.version_info < MIN_PYTHON:
        sys.exit("PAnalizer requires Python %d.%d or newer (found %s)."
                 % (MIN_PYTHON + (sys.version.split()[0],)))
    cmd = [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS]
    print(">>> " + " ".join(cmd))
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
