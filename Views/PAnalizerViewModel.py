import os
import re
from shutil import copy
from PAnalizerView_ui import *
from ImageScanner import *
from PyQt5.QtWidgets import QFileDialog

class MainWindow(QtWidgets.QMainWindow,Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)
        self.setupUi(self)

        #conctando eventos con acciones
        self.SearchDirectoryButton.clicked.connect(self.OnSearchDirectoryButtonClick)
        self.SearchLearnButton.clicked.connect(self.OnSearchLearnButtonClick)
        self.SearchResultButton.clicked.connect(self.OnLearnResultButtonClick)
        self.FaceSearchButton.clicked.connect(self.OnFaceSearchButtonClick)
        self.NudeSearchButton.clicked.connect(self.OnNudeSearchButtonClick)


    def OnSearchDirectoryButtonClick(self):
        directoryName = str(QFileDialog.getExistingDirectory(self, "Seleccione Carpeta"))
        self.DirectorySearch.setPlainText(directoryName)

    def OnSearchLearnButtonClick(self):
        directoryName = str(QFileDialog.getExistingDirectory(self, "Seleccione Carpeta"))
        self.DirectoryLearn.setPlainText(directoryName)

    def OnLearnResultButtonClick(self):
        directoryName = str(QFileDialog.getExistingDirectory(self, "Seleccione Carpeta"))
        self.DirectoryResult.setPlainText(directoryName)

    def OnFaceSearchButtonClick(self):
        searchPath = str(self.DirectorySearch.toPlainText())
        learnPath = str(self.DirectoryLearn.toPlainText())
        resultPath = str(self.DirectoryResult.toPlainText())
        if os.path.isdir(searchPath) and os.path.isdir(resultPath) and os.path.isdir(learnPath) and searchPath != resultPath:
            self.progressBar.setValue(0)
            #totalFiles = len(os.walk(searchPath))
            #progressBarStep = totalFiles / 100
            recognizer = TrainRecognizer(learnPath)
            for base, dirs, files in os.walk(searchPath):
                #count += progressBarStep
                #self.progressBar.setValue(count)
                for fileName in files:
                    fullName = str(os.path.join(base, fileName))
                    image = cv2.imread(fullName)
                    if image is not None:
                        prediction = Recognize(recognizer,image,50)
                        if prediction:
                            self.ShowResultText.appendPlainText(fullName + '\n')
                            copy(src = fullName, dst = resultPath+fileName)                            

    def OnNudeSearchButtonClick(self):
        searchPath = str(self.DirectorySearch.toPlainText())
        resultPath = str(self.DirectoryResult.toPlainText())
        if os.path.isdir(searchPath) and os.path.isdir(resultPath) and searchPath != resultPath:
            self.progressBar.setValue(0)
            #totalFiles = len(dirpath)
            #progressBarStep = totalFiles / 100
            for base, dirs, files in os.walk(searchPath):
                #count += progressBarStep
                #self.progressBar.setValue(count)                
                for fileName in files:
                    fullName = str(os.path.join(base, fileName))
                    image = cv2.imread(fullName)
                    if image is not None:
                        bodies = BodySearch(image)
                        if bodies is not None:
                            for item in bodies:
                                hasNude = SkinScan(item)
                                if hasNude:
                                    self.ShowResultText.appendPlainText(fullName + '\n')
                                    destinyName = str(os.path.join(resultPath, fileName))
                                    copy(src = fullName, dst = destinyName)
                                    break

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()

