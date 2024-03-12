# -*- coding: utf-8 -*-
"""
Created on Sun Sep 24 13:59:01 2023

@author: zhaohuiyu
"""

"""
System modules
"""
import ctypes
"""
Third-party Modules
"""
import numpy as np
from PyQt5 import QtWidgets

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure

"""
User Modules
"""


'''' *************************************** '''
'''         DO NOT MODIFY THIS FILE          '''
'''' *************************************** '''

class QtMatplotCanvas(FigureCanvas):
    
    def __init__(self, *args, **kwargs):
        super(QtMatplotCanvas, self).__init__( *args, **kwargs)
        


class Plot1DWidget(QtWidgets.QWidget):
    #sendMsgSignal = QtCore.pyqtSignal(int)
    
    def __init__(self, *args, **kwargs):
        super(Plot1DWidget, self).__init__( *args, **kwargs)
        
        self.initNonUiMembers()        
        self.initUiMembers()
        self.initUiLayout()
        
    
    def initUiMembers(self):
        #Canvas
        #hdc = ctypes.windll.user32.GetDC(0)
        #device_dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
        self.canvas = QtMatplotCanvas(Figure(figsize=(5, 3), dpi = 100)) #device_dpi))
        self.canvas.figure.subplots_adjust(left=0.1, bottom=0.09, right=0.95, top=0.93)
        self.canvas.figure.patch.set_visible(True)
        
        self.ui_pb_real_time_dIdV = QtWidgets.QPushButton('Real time dI/dV curve')
        self.ui_pb_real_time_dIdV.setCheckable(True)
        
        self.ax = self.canvas.figure.add_subplot(1,1,1)
        self.curve = self.ax.plot(self.energy, [])
        
        
    def initUiLayout(self):
        # Layout       
        self.ui_verticalLayout = QtWidgets.QVBoxLayout()
        self.ui_verticalLayout.setContentsMargins(0,0,0,0) # left, top, right, bottom
        self.ui_verticalLayout.addWidget(self.ui_pb_real_time_dIdV)
        self.ui_verticalLayout.addWidget(self.canvas)
        
        self.ui_gridlayout = QtWidgets.QGridLayout()
        self.ui_gridlayout.addLayout(self.ui_verticalLayout, 0, 0, 1, 1)
        self.ui_gridlayout.setContentsMargins(0,0,0,0) # left, top, right, bottom
        
        self.setLayout(self.ui_gridlayout)     
        
        
    def initNonUiMembers(self):
        self.uds_Var = 0
        self.data_3D = []
        self.energy = []
        self.frontsize = 11
        self.labelsize = 9
        
        
    def setDataFromImage2or3D(self, uds_Var):
        self.uds_Var = uds_Var
        self.data_3D = self.uds_Var.data
        self.energy = uds_Var.info['LayerValue']
        
    
    def setXYFromImage2or3D(self, x, y):
        x_Position = x
        y_Position = y
        
        if self.ui_pb_real_time_dIdV.isChecked():
            data_1D = self.data_3D[ :, y_Position, x_Position]
        
            yavg = np.max(self.data_3D, axis = 0).mean()
            ystd = np.max(self.data_3D, axis = 0).std()
            ylim_min = np.min(self.data_3D)
        
            self.ax.clear()
            self.ax.plot(self.energy, data_1D, color = 'k', linewidth = 1.0)
        
            self.ax.set_xlabel('Bias(mV)', size = self.frontsize)
            self.ax.set_ylabel('dI/dV', size = self.frontsize)
            self.ax.minorticks_on()
            #self.ax.yaxis.get_major_formatter().set_powerlimits((0,1))
            self.ax.tick_params(axis='both', which = 'both', direction = 'in', labelsize = self.labelsize)
            self.ax.set_ylim(ylim_min, yavg + 3*ystd)
            self.canvas.figure.tight_layout()
            self.ax.figure.canvas.draw()
            
        
    def setPickedPointsListFromImage2or3D(self, picked_points_list):
        dIdV_set = np.zeros((len(picked_points_list), len(self.energy)))
        for i in range(len(picked_points_list)):
            x = int(picked_points_list[i].split(',')[0])
            y = int(picked_points_list[i].split(',')[1])
            
            d_r = self.data_3D.shape[-2]
            d_c = self.data_3D.shape[-1]
            if x >= 0 and x < d_c and y >= 0 and y < d_r :
                dIdV_set[i,:] = self.data_3D[ :, y, x]
            
        yavg = np.max(self.data_3D, axis = 0).mean()
        ystd = np.max(self.data_3D, axis = 0).std()
        ylim_min = np.min(self.data_3D)
        
        self.ax.clear()
        for i in range(len(picked_points_list)):
            self.ax.plot(self.energy, dIdV_set[i,:], linewidth = 1.0)
        
        self.ax.set_xlabel('Bias(mV)', size = self.frontsize)
        self.ax.set_ylabel('dI/dV', size = self.frontsize)
        self.ax.minorticks_on()
        self.ax.tick_params(axis='both', which = 'both', direction = 'in', labelsize = self.labelsize)
        self.ax.set_ylim(ylim_min, yavg + 3*ystd)
        self.canvas.figure.tight_layout()
        self.ax.figure.canvas.draw()
        
        
    def setLineCutStartAndEndPoints(self, Points_list): 
        start_x = Points_list[0][0]
        start_y = Points_list[0][1]
        
        end_x = Points_list[1][0]
        end_y = Points_list[1][1]
        
        
        if start_x == end_x: # equal x
            if start_y > end_y:
                a = end_y
                end_y = start_y
                start_y = a
            dIdV_set = np.zeros( (end_y - start_y + 1 , len(self.energy) ) ) 
            for i in range(start_y, end_y + 1):
                dIdV_set[i-start_y, :] = self.data_3D[:, i, start_x]
        elif start_y == end_y: # equal y
            if start_x > end_x:
                a = end_x
                end_x = start_x
                start_x = a
            dIdV_set = np.zeros( (end_x - start_x + 1 , len(self.energy) ) )
            for i in range(start_x,end_x + 1):
                dIdV_set[i-start_x, :] = self.data_3D[:, start_y, i]
        
        delta_Y = (np.max(dIdV_set, axis = 1) - np.min(dIdV_set, axis = 1)).mean()
        
        self.ax.clear()
        for i in range(dIdV_set.shape[0]):
            self.ax.plot(self.energy, dIdV_set[i,:] + i * 0.1 * delta_Y, color = 'k', linewidth = 1.0)
        
        self.ax.set_xlabel('Bias(mV)', size = self.frontsize)
        self.ax.set_ylabel('dI/dV', size = self.frontsize)
        self.ax.minorticks_on()
        self.ax.tick_params(axis='both', which = 'both', direction = 'in', labelsize = self.labelsize)
        self.canvas.figure.tight_layout()
        self.ax.figure.canvas.draw()
        