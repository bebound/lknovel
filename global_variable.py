# global variables

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0'}

HAS_QT = False

try:
    from PyQt4 import QtCore

    HAS_QT = True
except:
    pass

if HAS_QT:
    class SenderObject(QtCore.QObject):
        sigChangeStatus = QtCore.pyqtSignal(str)
        sigWarningMessage = QtCore.pyqtSignal(str, str)
        sigInformationMessage = QtCore.pyqtSignal(str, str)
        sigButton = QtCore.pyqtSignal()

    SENDER = SenderObject()