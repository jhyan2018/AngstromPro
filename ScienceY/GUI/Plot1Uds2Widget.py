# -*- coding: utf-8 -*-
"""
Created on Tue May 21 16:21:44 2024

@author: jiahao 
"""

"""
System modules
"""

"""
Third-party Modules
"""
import numpy as np
from PyQt5 import QtCore, QtWidgets

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure
from matplotlib import colors,pyplot

"""
User Modules
"""
from ..RawDataProcess.UdsDataProcess import UdsDataStru
from .general.NumberExpression import NumberExpression

""" *************************************** """
""" DO NOT MODIFY THIS FILE"""
""" *************************************** """

class QtMatplotCanvas(FigureCanvas):
    mouseMoveEventSignal = QtCore.pyqtSignal(QtCore.QEvent)
    mousePressEventSignal = QtCore.pyqtSignal(QtCore.QEvent)
    mouseReleaseEventSignal = QtCore.pyqtSignal(QtCore.QEvent)
    wheelEventSignal = QtCore.pyqtSignal(QtCore.QEvent)
    
    def __init__(self, *args, **kwargs):
        super(QtMatplotCanvas, self).__init__( *args, **kwargs)
        
        self.setMouseTracking(True)
        
    def getWidgetWidth(self):
        return self.frameGeometry().width()
    
    def getWidgetHeight(self):
        return self.frameGeometry().height()
        
        
    def mouseMoveEvent(self, event):
        self.mouseMoveEventSignal.emit(event)
        
    def mousePressEvent(self, event):
        self.mousePressEventSignal.emit(event)
        
    def mouseReleaseEvent(self, event):
        self.mouseReleaseEventSignal.emit(event)
        
    def wheelEvent(self, event):
        self.wheelEventSignal.emit(event)
        



class Plot1Uds2Widget(QtWidgets.QWidget):
    sendMsgSignal = QtCore.pyqtSignal(int)
    
    def __init__(self, *args, **kwargs):
        super(Plot1Uds2Widget, self).__init__( *args, **kwargs)
        
        self.initNonUiMembers()        
        self.initUiMembers()
        self.initUiLayout()
        
    def initUiMembers(self):
        # Canvas
        self.static_canvas = QtMatplotCanvas(Figure(figsize=(10, 10), dpi = 100))
        #self.static_canvas.figure.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=None, hspace=None)
        #self.static_canvas.figure.patch.set_visible( False )
        
        self.static_ax = self.static_canvas.figure.add_subplot(1,1,1)
        #self.static_image = self.static_ax.imshow(np.ones((200,200)),interpolation = 'nearest',aspect = 'auto')
    
    def initNonUiMembers(self):
        pass
    
    def initUiLayout(self):
        
        ui_gridlayout = QtWidgets.QGridLayout()
        ui_gridlayout.addWidget(self.static_canvas, 0, 0)
        ui_gridlayout.setContentsMargins(0,0,0,0) # left, top, right, bottom
        
        self.setLayout(ui_gridlayout)
        
    def setCanvasWidgetSize(self, w, h):
        self.static_canvas.setFixedWidth(w)
        self.static_canvas.setFixedHeight(h)
        
    def setUdsData(self, uds_data):
        print('plot 1d set data')
        self.static_ax.clear()
        
        x_axis = range(uds_data.data.shape[1])
        for i in range(uds_data.data.shape[0]):
            self.static_ax.plot( uds_data.data[i,:] + i*5e-9, linewidth = 1.0, label='c'+str(i))
        
        self.static_ax.set_xlabel('Energy (V)', fontsize=20)
        self.static_ax.set_ylabel('Intensity (S)', fontsize=20)
        self.static_ax.set_title('dI/dV', fontsize=20)
        
        self.static_ax.tick_params(axis='x', labelsize=18)
        self.static_ax.tick_params(axis='y', labelsize=18)
        #self.static_ax.legend()
        
        #self.static_ax.grid(True)
        
        #self.static_ax.set(xlim=(0,300),ylim=(0,300))
        
        self.static_ax.figure.canvas.draw()
        self.static_canvas.flush_events()