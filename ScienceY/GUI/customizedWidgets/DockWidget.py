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
from ScienceY.qt_compt import QtWidgets, Signal

"""
User Modules
"""

"""
Module Definition
"""

class DockWidget(QtWidgets.QDockWidget):
    resizeSignal = Signal()
    
    def __init__(self, *args, **kwargs):
        super(DockWidget, self).__init__( *args, **kwargs)
        
    def resizeEvent(self, event):
        self.resizeSignal.emit()