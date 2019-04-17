from PyQt5 import QtWidgets

from ViewModels import PAnalizerViewModel
from Views import PAnalizerView_ui
from Libs import ImageScanner

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    CurrentWindow = PAnalizerViewModel.MainWindow()
    CurrentWindow.show()
    app.exec_()
