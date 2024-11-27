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
from .PlotConfigWidget import PlotConfigKey, PlotConfig, PlotObjManager, PlotConfigHandler

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
        self.static_canvas = QtMatplotCanvas(Figure(figsize=(20, 20), dpi = 200))
        self.plot_obj_mgr.set_figure(self.static_canvas.figure)
        
        #        
        static_ax = self.static_canvas.figure.add_subplot(1,1,1)
        self.plot_obj_mgr.add_axis(static_ax)
        
    def initNonUiMembers(self):
        self.uds_data_list = []
        self.udata_name_list = []
        self.plot_obj_mgr = PlotObjManager()
        
        self.cfg_key = PlotConfigKey()
    
    def initUiLayout(self):
        
        ui_gridlayout = QtWidgets.QGridLayout()
        ui_gridlayout.addWidget(self.static_canvas, 0, 0)
        ui_gridlayout.setContentsMargins(0,0,0,0) # left, top, right, bottom
        
        self.setLayout(ui_gridlayout)
        
    def setCanvasWidgetSize(self, w, h):
        self.static_canvas.setFixedWidth(w)
        self.static_canvas.setFixedHeight(h)
        self.static_canvas.figure.tight_layout()
        self.static_canvas.figure.canvas.draw()
        
    def get_fig_obj(self):
        return self.plot_obj_mgr.get_figure()
        
    def get_axis_obj(self):
        return self.plot_obj_mgr.get_aixs()
    
    def get_line(self, udata_name, curve_idx):
        return self.plot_obj_mgr.get_curve(udata_name, curve_idx)
        
    def plotLines(self, uds_data_idx):
        uds_data = self.uds_data_list[uds_data_idx]
        #
        if len(uds_data.axis_value[0]) > 0:
            x_axis = np.array(uds_data.axis_value[-1])
        else:
            x_axis = range(uds_data.data.shape[1])
        
        #   
        for i in range(uds_data.data.shape[0]):
            line, = self.plot_obj_mgr.get_aixs().plot(x_axis, uds_data.data[i,:])
            self.plot_obj_mgr.add_curve_to_axis(uds_data.name, line)
        
        self.static_canvas.figure.tight_layout()
        self.plot_obj_mgr.get_aixs().figure.canvas.draw()
    
    def loadPresetConfig(self, uds_data):
        plot_config_hdlr = PlotConfigHandler()        
        
        if 'Plot_Config' not in uds_data.config:
            uds_data.config['Plot_Config'] = PlotConfig()
            c_k = self.cfg_key
            
            # axis config            
            config=dict()
            config[c_k.X_LABEL] = uds_data.axis_name[-1]
            if 'Data_Name_Unit' in uds_data.info:
               config[c_k.Y_LABEL] = uds_data.info['Data_Name_Unit']
               
            uds_data.config['Plot_Config'].update_axis_config(config)
        
        #
        plot_config_hdlr.apply_axis_config(self.plot_obj_mgr.get_aixs(), uds_data.config['Plot_Config'].config_axis)
        
        # line config
        for i in range(uds_data.data.shape[0]):
            uds_data.config['Plot_Config'].add_config_line()
            plot_config_hdlr.apply_line_config(self.get_line(uds_data.name,i), uds_data.config['Plot_Config'].config_line_list[i])
        
        #             
        self.static_canvas.figure.tight_layout()
        self.static_canvas.figure.canvas.draw()
    
    def setUdsData(self, uds_data):
        if len(uds_data.data.shape) == 2:
            self.uds_data_list = []
            self.plot_obj_mgr.get_aixs().clear()
            
            self.addUdsData(uds_data)                
        else:
            print('Unaccepted data dimension!')
            return -1
    
    def addUdsData(self, uds_data):
        if len(uds_data.data.shape) == 2:
            self.uds_data_list.append(uds_data)            
            uds_data_idx = len(self.uds_data_list) - 1
            self.plotLines(uds_data_idx)
            
            self.loadPresetConfig(uds_data)
        else:
            print('Unaccepted data dimension!')
            return -1