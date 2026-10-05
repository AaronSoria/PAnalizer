# onnxruntime (used by NudeNet) must be imported before PyQt5. On Windows,
# PyQt5 bundles an older Microsoft C++ runtime (msvcp140.dll) than onnxruntime
# needs; whichever loads first is used by the whole process, and loading
# PyQt5's copy first makes onnxruntime crash with an access violation.
import onnxruntime  # noqa: F401

from PyQt5 import QtWidgets

from ViewModels import PAnalizerViewModel

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    CurrentWindow = PAnalizerViewModel.MainWindow()
    CurrentWindow.show()
    app.exec_()
