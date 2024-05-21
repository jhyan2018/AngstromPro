# -*- coding: utf-8 -*-
"""
Created on Fri May 17 13:38:34 2024

@author: jiahao yan
"""

"""
System modules
"""

"""
Third-party Modules
"""
from PyQt5 import QtCore, QtWidgets

"""
User Modules
"""

"""
Module Definition
"""

class DockWidget(QtWidgets.QDockWidget):
    resizeSignal = QtCore.pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        super(DockWidget, self).__init__( *args, **kwargs)
        
    def resizeEvent(self, event):
        self.resizeSignal.emit()