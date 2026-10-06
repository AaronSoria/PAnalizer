"""Behavior of the main window, driven through the worker signal handlers."""

import os

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


def test_matches_are_listed_with_score_and_copy(window, tmp_path):
    images, results = str(tmp_path / "images"), str(tmp_path / "results")
    match = os.path.join(images, "phone", "a.jpg")
    window._search_root = images
    window._on_result_found(match, 0.6612, os.path.join(results, "a.jpg"))
    window._on_result_found(os.path.join(images, "b.jpg"), 0.5, "")

    table = window.ResultsTable
    rows = [[table.item(r, c).text() for c in range(3)] for r in range(table.rowCount())]
    assert rows[0] == [os.path.join("phone", "a.jpg"), "0.66", "a.jpg"]
    assert rows[1] == ["b.jpg", "0.50", "copy failed"]
    assert table.item(0, 0).toolTip() == match


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


def _fill_and_start(window, monkeypatch, search, learn, result):
    monkeypatch.setattr(window, "_start", lambda worker, message: None)
    window.DirectorySearch.setText(str(search))
    window.DirectoryLearn.setText(str(learn))
    window.DirectoryResult.setText(str(result))
    window.OnFaceSearchButtonClick()


def test_folders_are_remembered_between_sessions(window, monkeypatch, tmp_path):
    folders = [tmp_path / n for n in ("search", "learn", "results")]
    for d in folders:
        d.mkdir()
    _fill_and_start(window, monkeypatch, *folders)

    reopened = PAnalizerViewModel.MainWindow()
    assert [reopened.DirectorySearch.text(), reopened.DirectoryLearn.text(), reopened.DirectoryResult.text()] \
        == [str(d) for d in folders]
    reopened.close()


def test_missing_remembered_folders_are_not_restored(window, monkeypatch, tmp_path):
    folders = [tmp_path / n for n in ("search", "learn", "results")]
    for d in folders:
        d.mkdir()
    _fill_and_start(window, monkeypatch, *folders)
    folders[1].rmdir()

    reopened = PAnalizerViewModel.MainWindow()
    assert reopened.DirectoryLearn.text() == ""
    assert reopened.DirectorySearch.text() == str(folders[0])
    reopened.close()


def test_forget_recent_folders(window, monkeypatch, tmp_path):
    folders = [tmp_path / n for n in ("search", "learn", "results")]
    for d in folders:
        d.mkdir()
    _fill_and_start(window, monkeypatch, *folders)
    window.actionForgetFolders.trigger()

    reopened = PAnalizerViewModel.MainWindow()
    assert (reopened.DirectorySearch.text(), reopened.DirectoryLearn.text(), reopened.DirectoryResult.text()) \
        == ("", "", "")
    assert not any(PAnalizerViewModel.MainWindow._settings().allKeys())
    reopened.close()


def test_thresholds_start_at_defaults(window):
    assert window.thresholds == {"nudity": 0.6, "face": 0.363, "detection": 0.7}
    assert window.thresholdsLabel.text().endswith("— defaults")
    assert "nudity ≥ 0.60" in window.thresholdsLabel.text()


def test_thresholds_dialog_restore_defaults(window):
    dialog = PAnalizerViewModel.ThresholdsDialog({"nudity": 0.8, "face": 0.5, "detection": 0.5}, window)
    assert dialog.Values() == {"nudity": 0.8, "face": 0.5, "detection": 0.5}
    dialog.buttonBox.button(QtWidgets.QDialogButtonBox.RestoreDefaults).click()
    assert dialog.Values() == PAnalizerViewModel.DEFAULT_THRESHOLDS


def test_thresholds_dialog_clamps_to_allowed_range(window):
    dialog = PAnalizerViewModel.ThresholdsDialog({"nudity": 5.0, "face": -1.0, "detection": 0.0}, window)
    assert dialog.Values() == {"nudity": 0.99, "face": 0.1, "detection": 0.3}


def _accept_dialog_with(monkeypatch, values):
    def fake_exec(dialog):
        dialog.SetValues(values)
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(PAnalizerViewModel.ThresholdsDialog, "exec_", fake_exec)


def test_edited_thresholds_are_shown_and_used(window, monkeypatch, tmp_path):
    _accept_dialog_with(monkeypatch, {"nudity": 0.75, "face": 0.45, "detection": 0.55})
    window.ThresholdsButton.click()
    assert window.thresholdsLabel.text() == (
        "Thresholds: nudity ≥ 0.75 · face similarity ≥ 0.450 · face detection ≥ 0.55 — modified for this session")
    assert window.thresholdsLabel.property("modified") is True

    started = []
    monkeypatch.setattr(window, "_start", lambda worker, message: started.append(worker))
    for name in ("search", "learn", "results"):
        (tmp_path / name).mkdir()
    window.DirectorySearch.setText(str(tmp_path / "search"))
    window.DirectoryLearn.setText(str(tmp_path / "learn"))
    window.DirectoryResult.setText(str(tmp_path / "results"))
    window.OnNudeSearchButtonClick()
    window.OnFaceSearchButtonClick()
    assert started[0].threshold == 0.75
    assert (started[1].threshold, started[1].detection_score) == (0.45, 0.55)


def test_cancelled_dialog_keeps_thresholds(window, monkeypatch):
    monkeypatch.setattr(PAnalizerViewModel.ThresholdsDialog, "exec_", lambda dialog: QtWidgets.QDialog.Rejected)
    window.actionThresholds.trigger()
    assert window.thresholds == PAnalizerViewModel.DEFAULT_THRESHOLDS


def test_thresholds_are_not_remembered_between_sessions(window, monkeypatch):
    _accept_dialog_with(monkeypatch, {"nudity": 0.9, "face": 0.6, "detection": 0.9})
    window.ThresholdsButton.click()
    reopened = PAnalizerViewModel.MainWindow()
    assert reopened.thresholds == PAnalizerViewModel.DEFAULT_THRESHOLDS
    reopened.close()


def test_thresholds_locked_while_running(window):
    window._set_ui_running(True)
    assert not window.ThresholdsButton.isEnabled() and not window.actionThresholds.isEnabled()
    window._set_ui_running(False)
    assert window.ThresholdsButton.isEnabled() and window.actionThresholds.isEnabled()
