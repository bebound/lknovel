import sys
import re
import os
import threading
from PyQt4 import QtCore, QtGui
import ui_mainWindow
import ui_helpWidget
import ui_aboutWidget
import lk2epub


class HelpWidget(QtGui.QDialog, ui_helpWidget.Ui_Dialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setupUi(self)
        self.setFixedSize(380, 190)

        self.pushButton.clicked.connect(lambda: self.close())


class AboutWidget(QtGui.QDialog, ui_aboutWidget.Ui_Dialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setupUi(self)
        self.setFixedSize(320, 120)

        self.pushButton.clicked.connect(lambda: self.close())


class MainWindow(QtGui.QMainWindow, ui_mainWindow.Ui_MainWindow):
    sigWarningMessage = QtCore.pyqtSignal(str, str)
    sigInformationMessage = QtCore.pyqtSignal(str, str)

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.setFixedSize(520, 250)
        self.urlLineEdit.installEventFilter(self)
        self.setWindowTitle('lknovel-轻之国度在线轻小说转epub')
        self.helpAction = QtGui.QAction('&Help', self)
        self.helpAction.setStatusTip('使用说明')
        self.aboutAction = QtGui.QAction('&About', self)
        self.aboutAction.setStatusTip('关于')
        self.menubar.addAction(self.helpAction)
        self.menubar.addAction(self.aboutAction)
        self.setting = QtCore.QSettings('kk', 'lknovel')
        if self.setting.value('savePath'):
            self.savePath=self.setting.value('savePath')
        else:
            self.savePath = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.directoryLineEdit.setText(self.savePath)
        self.coverPath = ''

        self.startButton.clicked.connect(self.createEpub)
        self.sigInformationMessage.connect(self.showInformationMessage)
        self.sigWarningMessage.connect(self.showWarningMessage)
        self.directoryButton.clicked.connect(self.selectSaveDirectory)
        self.coverButton.clicked.connect(self.selectCover)
        lk2epub.sender.sigChangeStatus.connect(self.changeStatus)
        lk2epub.sender.sigWarningMessage.connect(self.showWarningMessage)
        lk2epub.sender.sigInformationMessage.connect(self.showInformationMessage)
        lk2epub.sender.sigButton.connect(lambda: self.startButton.setEnabled(True))
        self.helpAction.triggered.connect(self.openHelpWidget)
        self.aboutAction.triggered.connect(self.openAboutWidget)


    def createEpub(self):
        url = self.urlLineEdit.text()
        ok = 0
        check = re.compile(r'http://lknovel.lightnovel.cn/main/vollist/(\d+).html')
        check2 = re.compile(r'http://lknovel.lightnovel.cn/main/book/(\d+).html')
        if check.search(url) or check2.search(url):
            ok = 1
        if ok:
            self.setting.setValue('savePath', self.savePath)
            if url.split('/')[-2] == 'book':
                t = threading.Thread(target=lk2epub.parseVolume, args=(url, self.savePath, self.coverPath))
                t.start()
            else:
                t = threading.Thread(target=lk2epub.parseList, args=(url, self.savePath, self.coverPath))
                t.start()
            self.startButton.setEnabled(False)
        else:
            self.sigWarningMessage.emit('网址错误',
                                        '请输入正确的网址，例如：\nhttp://lknovel.lightnovel.cn/main/vollist/726.html\nhttp://lknovel.lightnovel.cn/main/book/2664.html')


    def selectSaveDirectory(self):
        tempPath = str(QtGui.QFileDialog.getExistingDirectory(self, "选择文件夹"))
        if tempPath:
            self.savePath = tempPath
            self.directoryLineEdit.setText(self.savePath)

    def selectCover(self):
        tempPath = str(
            QtGui.QFileDialog.getOpenFileNameAndFilter(self, "选择文件", os.path.join(os.path.expanduser('~'), 'Desktop'),
                                                       self.tr('图片文件(*.png *.jpg)'))[0])
        if tempPath:
            self.coverPath = tempPath
            self.coverLineEdit.setText(self.coverPath)

    def workDone(self):
        self.changeStatus('')
        self.sigInformationMessage.emit('完成', 'EPUB已生成')
        self.startButton.setEnabled(True)

    def openHelpWidget(self):
        self.helpWidget = HelpWidget()
        self.helpWidget.show()

    def openAboutWidget(self):
        self.aboutWidget = AboutWidget()
        self.aboutWidget.show()

    def changeStatus(self, text):
        self.statusbar.showMessage(text)

    #窗口激活时检测剪贴板 符合url规则自动填充至urlLineEdit
    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.WindowActivate:
            clipboardText = QtGui.QApplication.clipboard().text()
            check = re.compile(r'http://lknovel.lightnovel.cn/main/vollist/(\d+).html')
            check2 = re.compile(r'http://lknovel.lightnovel.cn/main/book/(\d+).html')
            if check.search(clipboardText) or check2.search(clipboardText):
                self.urlLineEdit.setText(clipboardText)
        return False

    def showWarningMessage(self, title, content):
        QtGui.QMessageBox.warning(self, title, content, buttons=QtGui.QMessageBox.Ok,
                                  defaultButton=QtGui.QMessageBox.NoButton)


    def showInformationMessage(self, title, content):
        QtGui.QMessageBox.information(self, title, content, buttons=QtGui.QMessageBox.Ok,
                                      defaultButton=QtGui.QMessageBox.NoButton)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    lkMainWidndow = MainWindow()
    lkMainWidndow.show()
    app.exec_()