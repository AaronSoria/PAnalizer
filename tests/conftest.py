import os
import sys

# Run Qt without a display (CI, headless servers).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Make the project root importable (PAnalizer is not an installed package).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
