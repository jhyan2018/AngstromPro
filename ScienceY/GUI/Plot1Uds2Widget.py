# -*- coding: utf-8 -*-
"""
Created on Tue May 21 16:21:44 2024

@author: jiahao 
"""

"""
System modules
"""
import re, math
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
        
        self.x_axis_prefix = ''
        self.x_axis_scale_factor = 1
    
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
    
    def auto_scale_x_axis(self, x_axis_value):
        x_axis_min = np.min(x_axis_value)
        x_axis_max = np.max(x_axis_value)       
        x_axis_abs_max = np.max([np.abs(x_axis_min), np.abs(x_axis_max)])
        
        order = math.floor(math.log10(x_axis_abs_max))
        # Create a lookup for common SI prefixes around the origin
        # Key is the "exponent group" in multiples of 3
        # Value is (prefix_string, exponent_of_10)
        si_prefixes = {
            -18: ('a', -18), # a
            -15: ('f', -15), # femto 
            -12: ("p", -12),  # pico
             -9:  ("n", -9),   # nano
             -6:  ("µ", -6),   # micro
             -3:  ("m", -3),   # milli
              0:  ("", 0),     # base
              3:  ("k", 3),    # kilo
              6:  ("M", 6),    # mega
              9:  ("G", 9),    # giga
             12:  ("T", 12)    # tera
        }
        
        # Round the order down to a multiple of 3 for typical SI prefixes
        multiple_of_three = int(3 * math.floor(order / 3))
    
        # Make sure the multiple_of_three is within your dictionary’s range
        # or clamp to the nearest known prefix.
        possible_exponents = sorted(si_prefixes.keys())
        min_exp = min(possible_exponents)
        max_exp = max(possible_exponents)
    
        if multiple_of_three < min_exp:
            multiple_of_three = min_exp
        elif multiple_of_three > max_exp:
            multiple_of_three = max_exp
    
        prefix, exponent = si_prefixes[multiple_of_three]
        scale_factor = 10 ** (-exponent)  # Because we want to multiply data by e.g. 1000 if exponent = -3
        
        return prefix, scale_factor
        
    def parse_axis_label(self, axis_label):
        """
        Parse a string of the form 'AxisName (Unit)' and return (AxisName, Unit).

        Example:
        input  -> "X (m)"
        output -> ("X", "m")
        """
        # Regular expression explanation:
        #   ^          : start of string
        #   \s*        : optional whitespace
        #   (.*?)      : capture any characters (non-greedy) as the axis name
        #   \s*\(      : optional whitespace before literal '('
        #   (.*?)      : capture any characters (non-greedy) as the unit
        #   \)         : literal ')'
        #   \s*$       : optional whitespace until end of string
        pattern = r'^\s*(.*?)\s*\((.*?)\)\s*$'
        match = re.match(pattern, axis_label)
        if match:
            axis_name = match.group(1)
            unit = match.group(2)

        else:
            axis_name = '?'
            unit = '?'
        
        return axis_name, unit
    
    def plotLines(self, uds_data_idx):
        uds_data = self.uds_data_list[uds_data_idx]
        
        #
        x_axis = np.array(uds_data.axis_value[-1])
        
        self.x_axis_prefix, self.x_axis_scale_factor = self.auto_scale_x_axis(x_axis)
        x_axis = x_axis * self.x_axis_scale_factor
        
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
            
            x_axis_name, x_axis_unit = self.parse_axis_label(uds_data.axis_name[-1])
            config[c_k.X_LABEL] = x_axis_name + ' (' + self.x_axis_prefix + x_axis_unit + ')'
            
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