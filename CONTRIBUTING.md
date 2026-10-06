# Contributing to PAnalizer

Thanks for your interest in improving PAnalizer.

## Reporting bugs

Open an issue using the **Bug report** template and include your operating
system, Python version (`python --version`), the output of `pip freeze`, and
the full error message.

**Never attach or link explicit or illegal images to an issue.** Describe the
problem in text, or reproduce it with harmless test images.

## Development setup

```bash
python -m venv .venv
# Linux/macOS: . .venv/bin/activate    Windows: .venv\Scripts\activate
pip install -r requirements.txt ruff pytest
```

Before opening a pull request, run:

```bash
ruff check .
pytest
```

Both run in CI on Linux and Windows for Python 3.11–3.13.

## Pull requests

- Keep each pull request focused on one change and describe what it does and
  how you tested it.
- `Views/*_ui.py` files are generated from the `Views/*.ui` forms. Edit the
  `.ui` file in Qt Designer and regenerate it, for example
  `pyuic5 Views/PAnalizerView.ui -o Views/PAnalizerView_ui.py`.
- Colors and spacing live in `Views/style.qss`. Keep the interface sober:
  neutral colors, one accent, and no thumbnails of analyzed images.
- By contributing you agree that your contributions are licensed under the
  [GNU Affero General Public License v3.0 or later](LICENSE).
