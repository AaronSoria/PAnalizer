"""Behavior of the main window, driven through the worker signal handlers."""

import pytest
from PyQt5 import QtWidgets

from ViewModels import PAnalizerViewModel


@pytest.fixture
def window():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w = PAnalizerViewModel.MainWindow()
    yield w
    w.close()
    assert app is not None


def test_idle_state(window):
    assert window.StopButton.isEnabled() is False
    assert window.OpenResultsButton.isEnabled() is False
    assert window.OpenLogButton.isEnabled() is False
    assert window.ResultsTable.rowCount() == 0
    assert window.progressLabel.text() == "Ready"


def test_matches_are_listed_with_score_and_copy(window):
    window._search_root = r"C:\case\images"
    window._on_result_found(r"C:\case\images\phone\a.jpg", 0.6612, r"C:\case\results\a.jpg")
    window._on_result_found(r"C:\case\images\b.jpg", 0.5, "")

    table = window.ResultsTable
    rows = [[table.item(r, c).text() for c in range(3)] for r in range(table.rowCount())]
    assert rows[0][1:] == ["0.66", "a.jpg"]
    assert rows[0][0].replace("/", "\\") == r"phone\a.jpg"
    assert rows[1][1:] == ["0.50", "copy failed"]
    assert table.item(0, 0).toolTip() == r"C:\case\images\phone\a.jpg"


def test_progress_and_finish_labels(window):
    window._on_result_found("x.jpg", 0.9, "y.jpg")
    window._on_progress(1287, 3410)
    assert window.progressLabel.text() == "1,287 / 3,410 images · 1 match"
    assert (window.progressBar.value(), window.progressBar.maximum()) == (1287, 3410)

    window._on_finished(3410, 1)
    assert window.progressLabel.text() == "Finished · 3,410 images · 1 match"


def test_running_state_and_stop(window):
    class FakeWorker:
        stopped = False

        def stop(self):
            self.stopped = True

    window._set_ui_running(True)
    window._worker = worker = FakeWorker()
    assert window.StopButton.isEnabled() and not window.FaceSearchButton.isEnabled()
    assert not window.DirectorySearch.isEnabled()

    window.OnStopButtonClick()
    assert worker.stopped is True
    assert window.StopButton.isEnabled() is False
    assert window.progressLabel.text() == "Stopping after the current image…"

    window._on_finished(10, 0)
    assert window.progressLabel.text() == "Stopped · 10 images · 0 matches"
    assert window.FaceSearchButton.isEnabled() and window._worker is None


def test_open_buttons_follow_results_folder_and_log(window, tmp_path):
    window.DirectoryResult.setText(str(tmp_path))
    assert window.OpenResultsButton.isEnabled() and window.actionOpenResults.isEnabled()
    assert not window.OpenLogButton.isEnabled()

    log = tmp_path / "panalizer_face_x.jsonl"
    log.write_text("{}\n")
    window._on_log_created(str(log))
    assert window.OpenLogButton.isEnabled() and window.actionOpenLog.isEnabled()

    window.DirectoryResult.setText(str(tmp_path / "missing"))
    assert not window.OpenResultsButton.isEnabled()


def test_missing_folder_shows_validation_message(window, monkeypatch):
    warnings = []
    monkeypatch.setattr(PAnalizerViewModel.QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    window.OnNudeSearchButtonClick()  # nothing selected
    assert warnings == ["Choose an existing folder of images to analyze."]


def test_failed_scan_is_not_reported_as_finished(window, monkeypatch):
    monkeypatch.setattr(PAnalizerViewModel.QMessageBox, "warning", lambda *args: None)
    window._on_failed("No face was detected in the reference photos.")
    window._on_finished(0, 0)
    assert window.progressLabel.text() == "Did not complete · 0 images · 0 matches"


def test_about_shows_version_license_and_warranty_notice():
    from Libs import __version__

    html = PAnalizerViewModel.ABOUT_HTML
    assert f"PAnalizer {__version__}" in html
    assert "GNU Affero General Public License" in html and "WITHOUT ANY WARRANTY" in html
    assert "NudeNet (AGPL-3.0)" in html and "https://github.com/AaronSoria/PAnalizer" in html


def test_about_action_opens_dialog(window, monkeypatch):
    shown = []
    monkeypatch.setattr(PAnalizerViewModel.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    window.actionAbout.trigger()
    assert len(shown) == 1 and "PAnalizer" in shown[0]
