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
from .PlotConfig import PlotConfig

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
        
        static_ax = self.static_canvas.figure.add_subplot(1,1,1)
        self.add_axis_item(static_ax, 1, 1)
        
    def initNonUiMembers(self):
        self.uds_data = None
        self.plot_config = None
        self.axis_list=[]
        self.line_list=[]
    
    def initUiLayout(self):
        
        ui_gridlayout = QtWidgets.QGridLayout()
        ui_gridlayout.addWidget(self.static_canvas, 0, 0)
        ui_gridlayout.setContentsMargins(0,0,0,0) # left, top, right, bottom
        
        self.setLayout(ui_gridlayout)
        
    def setCanvasWidgetSize(self, w, h):
        self.static_canvas.setFixedWidth(w)
        self.static_canvas.setFixedHeight(h)
    
    def add_axis_item(self, ax, nrow, ncol):
        axis_item = {'ax':None,
                     'subplot':None}
        axis_item['ax'] = ax        
        ax_idx = len(self.axis_list) 
        axis_item['subplot'] = [nrow, ncol, ax_idx]        
        self.axis_list.append(axis_item)
    
    def get_axis(self, ax_idx):
        return self.axis_list[ax_idx]['ax']
        
    def add_line_item(self, line, ax_idx):
        line_item = {'line':None,
                     'ax_idx':None}
        line_item['line'] = line
        line_item['ax_idx'] = ax_idx
        self.line_list.append(line_item)
        
    def get_line(self, line_idx):
        return self.line_list[line_idx]['line']
        
    def plotLines(self):
        self.get_axis(0) .clear()
        
        #
        if len(self.uds_data.axis_value[0]) > 0:
            x_axis = np.array(self.uds_data.axis_value[0])
        else:
            x_axis = range(self.uds_data.data.shape[1])
        
        #   
        for i in range(self.uds_data.data.shape[0]):
            line, = self.get_axis(0).plot(x_axis, self.uds_data.data[i,:])
            self.add_line_item(line, 0)
            
        self.get_axis(0).figure.canvas.draw()
        
    def setUdsData(self, uds_data):
        if len(uds_data.data.shape) == 2:
            self.line_list = []
            self.uds_data = uds_data
            self.plotLines()
            if 'Plot_Config' in uds_data.hidden_info:
                self.plot_config = uds_data.hidden_info['Plot_Config']
            else:
                self.plot_config = PlotConfig()
                
                # axis config
                self.plot_config.add_config_axis()
                config = {'xlabel':'Energy (V)',
                          'ylabel':'Intensity (S)',
                          'title':'dI/dV'}
                self.plot_config.update_axis_config(0, config)
                self.plot_config.apply_axis_config(self.get_axis(0) , 0)
                
                #self.get_axis(0).tick_params(axis='x', labelsize=18)
                #self.get_axis(0).tick_params(axis='y', labelsize=18)
                
                # line config
                for i in range(self.uds_data.data.shape[0]):
                    self.plot_config.add_config_line()
                    self.plot_config.apply_line_config(self.get_line(i) , i)
                
        else:
            print('Unaccepted data dimension!')
            return -1
        
    """ Dynamic Fucntions"""
        
        