import os
import sys

# Same reason as in PAnalizer.py: load onnxruntime before any test imports PyQt5.
import onnxruntime  # noqa: F401

# Run Qt without a display (CI, headless servers).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Make the project root importable (PAnalizer is not an installed package).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    """Keep remembered folders in a temporary INI file, never the user's real one."""
    from PyQt5.QtCore import QSettings

    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
