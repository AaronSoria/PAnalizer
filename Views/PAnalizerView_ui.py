# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'PAnalizerView.ui'
#
# Created by: PyQt5 UI code generator 5.7
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(621, 509)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(0, 0, 2, 2))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.DirectorySearch = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.DirectorySearch.setGeometry(QtCore.QRect(170, 10, 341, 40))
        self.DirectorySearch.setObjectName("DirectorySearch")
        self.DirectoryLearn = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.DirectoryLearn.setGeometry(QtCore.QRect(170, 60, 341, 40))
        self.DirectoryLearn.setObjectName("DirectoryLearn")
        self.SearchDirectoryButton = QtWidgets.QPushButton(self.centralwidget)
        self.SearchDirectoryButton.setGeometry(QtCore.QRect(530, 10, 81, 41))
        self.SearchDirectoryButton.setObjectName("SearchDirectoryButton")
        self.SearchLearnButton = QtWidgets.QPushButton(self.centralwidget)
        self.SearchLearnButton.setGeometry(QtCore.QRect(530, 60, 81, 41))
        self.SearchLearnButton.setObjectName("SearchLearnButton")
        self.FaceSearchButton = QtWidgets.QPushButton(self.centralwidget)
        self.FaceSearchButton.setGeometry(QtCore.QRect(10, 160, 271, 34))
        self.FaceSearchButton.setObjectName("FaceSearchButton")
        self.progressBar = QtWidgets.QProgressBar(self.centralwidget)
        self.progressBar.setGeometry(QtCore.QRect(10, 200, 601, 23))
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName("progressBar")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(10, 20, 151, 18))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(10, 70, 151, 18))
        self.label_2.setObjectName("label_2")
        self.NudeSearchButton = QtWidgets.QPushButton(self.centralwidget)
        self.NudeSearchButton.setGeometry(QtCore.QRect(340, 160, 271, 34))
        self.NudeSearchButton.setObjectName("NudeSearchButton")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(10, 120, 161, 18))
        self.label_3.setObjectName("label_3")
        self.DirectoryResult = QtWidgets.QTextEdit(self.centralwidget)
        self.DirectoryResult.setGeometry(QtCore.QRect(170, 110, 341, 41))
        self.DirectoryResult.setObjectName("DirectoryResult")
        self.SearchResultButton = QtWidgets.QPushButton(self.centralwidget)
        self.SearchResultButton.setGeometry(QtCore.QRect(530, 110, 81, 41))
        self.SearchResultButton.setObjectName("SearchResultButton")
        self.ShowResultText = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.ShowResultText.setGeometry(QtCore.QRect(10, 230, 599, 219))
        self.ShowResultText.setObjectName("ShowResultText")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 621, 30))
        self.menubar.setObjectName("menubar")
        self.menuAyuda = QtWidgets.QMenu(self.menubar)
        self.menuAyuda.setObjectName("menuAyuda")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionConfiguracion = QtWidgets.QAction(MainWindow)
        self.actionConfiguracion.setObjectName("actionConfiguracion")
        self.menuAyuda.addAction(self.actionConfiguracion)
        self.menubar.addAction(self.menuAyuda.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.SearchDirectoryButton.setText(_translate("MainWindow", "Buscar"))
        self.SearchLearnButton.setText(_translate("MainWindow", "Buscar"))
        self.FaceSearchButton.setText(_translate("MainWindow", "Busqueda por rostro"))
        self.label.setText(_translate("MainWindow", "Directorio para buscar:"))
        self.label_2.setText(_translate("MainWindow", "Directorio para aprender"))
        self.NudeSearchButton.setText(_translate("MainWindow", "Busqueda de desnudos"))
        self.label_3.setText(_translate("MainWindow", "Directorio para resultados"))
        self.SearchResultButton.setText(_translate("MainWindow", "Buscar"))
        self.menuAyuda.setTitle(_translate("MainWindow", "Ar&chivo"))
        self.actionConfiguracion.setText(_translate("MainWindow", "&Configuracion"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

