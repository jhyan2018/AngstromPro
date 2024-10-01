# -*- coding: utf-8 -*-
"""
Created on Sat May 18 16:23:59 2024

@author: jiahaoYan
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

class ScrollArea(QtWidgets.QScrollArea):
    resizeSignal = QtCore.pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        super(ScrollArea, self).__init__( *args, **kwargs)
        
    def resizeEvent(self, event):
        self.resizeSignal.emit()