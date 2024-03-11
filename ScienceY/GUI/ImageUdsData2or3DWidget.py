# -*- coding: utf-8 -*-
"""
Created on Mon Jul 31 16:21:57 2023

@author: Jiahao Yan
"""

"""
System modules
"""
import sys, os
import math

"""
Third-party Modules
"""
import numpy as np
from PyQt5 import QtCore, QtWidgets

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure

"""
User Modules
"""
from ..RawDataProcess.UdsDataStru import UdsDataStru3D

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
        



class ImageUdsData2or3DWidget(QtWidgets.QWidget):
    sendMsgSignal = QtCore.pyqtSignal(int)
    
    def __init__(self, *args, **kwargs):
        super(ImageUdsData2or3DWidget, self).__init__( *args, **kwargs)
        
        self.initNonUiMembers()        
        self.initUiMembers()
        self.initUiLayout()        
        
    def initUiMembers(self):
        # Canvas
        self.static_canvas = QtMatplotCanvas(Figure(figsize=(10, 10)))
        self.static_canvas.figure.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=None, hspace=None)
        self.static_canvas.figure.patch.set_visible( False )

        self.static_canvas.mouseMoveEventSignal.connect(self.canvasMouseMoveEvent)
        self.static_canvas.mousePressEventSignal.connect(self.canvasMousePressEvent)
        self.static_canvas.mouseReleaseEventSignal.connect(self.canvasMouseReleaseEvent)
        
        self.static_canvas.wheelEventSignal.connect(self.canvasWheelEvent)
        self.static_ax = self.static_canvas.figure.add_subplot(1,1,1)
        self.static_image = self.static_ax.imshow(np.ones((200,200)),interpolation = 'nearest',aspect = 'auto')
        
        self.static_canvas.setEnabled(False)  
        
        # other widgets
        self.ui_lb_widget_name = QtWidgets.QLabel()
        self.ui_pb_select_var =  QtWidgets.QPushButton("Select Variable")
        self.ui_pb_select_var.clicked.connect(self.selectVar)
        self.ui_lb_selected_var_name = QtWidgets.QLabel("Name: ")
        self.ui_le_selected_var = QtWidgets.QLineEdit()
        self.ui_le_image_data_type = QtWidgets.QLabel("Type: ")
        self.ui_cb_image_data_type = QtWidgets.QComboBox()
        self.ui_cb_image_data_type.addItems(self.var_data_type_list)
        self.ui_cb_image_data_type.currentIndexChanged.connect(self.imageDataTypeChanged)
        self.ui_cb_image_data_type.setEnabled(False)
        self.ui_lb_image_layer = QtWidgets.QLabel("Layer: ")
        self.ui_sb_image_layers = QtWidgets.QSpinBox()
        self.ui_sb_image_layers.valueChanged.connect(self.imageLayerChanged)
        self.ui_sb_image_layers.setEnabled(False)
        self.ui_le_layer_value = QtWidgets.QLineEdit()
        self.ui_le_layer_value.setEnabled(False)
        
        self.ui_vs_image_scale_upper =  QtWidgets.QSlider()
        self.ui_vs_image_scale_upper.setOrientation(QtCore.Qt.Vertical)
        self.ui_vs_image_scale_lower =  QtWidgets.QSlider()
        self.ui_vs_image_scale_lower.setOrientation(QtCore.Qt.Vertical)
        self.ui_sb_image_scale_min = QtWidgets.QDoubleSpinBox()
        self.ui_sb_image_scale_max = QtWidgets.QDoubleSpinBox()
        self.ui_sb_image_scale_spacer = QtWidgets.QSpacerItem(20, 50)
        self.ui_sb_image_scale_max.valueChanged.connect(self.imgeScaleChanged)                
        self.ui_sb_image_scale_min.valueChanged.connect(self.imgeScaleChanged)
        
        self.ui_lb_img_palette = QtWidgets.QLabel("Palette: ")
        self.ui_cb_img_palette_list = QtWidgets.QComboBox()

        self.ui_lb_img_picked_points = QtWidgets.QLabel("Picked Points: ")
        self.ui_cb_img_pk_pts_palette_list = QtWidgets.QComboBox()
        
        self.ui_lw_img_picked_points_list_widgets = QtWidgets.QListWidget()
        self.ui_pb_img_picked_points_remove = QtWidgets.QPushButton("Remove Point")
        self.ui_pb_img_picked_points_remove.clicked.connect(self.removePickedPoint)
        self.ui_lb_img_proc_parameter = QtWidgets.QLabel("Params (p1,p2,...): ")
        self.ui_le_img_proc_parameter_list = QtWidgets.QLineEdit()
        self.ui_lb_img_to_data_coord = QtWidgets.QLabel("Data coords（column, row）: ")
        self.ui_le_img_to_data_coordinate = QtWidgets.QLineEdit()
        self.ui_lb_uds_data_info =  QtWidgets.QLabel("Info: ")
        self.ui_lw_uds_data_info = QtWidgets.QListWidget()
        
        # Color Maps 
        self.ui_cb_img_palette_list.addItems(self.img_color_map_list)        
        self.ui_cb_img_palette_list.currentIndexChanged.connect(self.imageColorMapChanged)
        
        self.ui_cb_img_pk_pts_palette_list.addItems(self.img_marker_cn_list)       
        self.ui_cb_img_pk_pts_palette_list.currentIndexChanged.connect(self.imageMarkerColorChanged)
        
    def initUiLayout(self):   
        # Layout Top                
        self.ui_verticalLayout_scale_1 = QtWidgets.QVBoxLayout()
        self.ui_verticalLayout_scale_1.addWidget(self.ui_sb_image_scale_max)
        self.ui_verticalLayout_scale_1.addItem(self.ui_sb_image_scale_spacer)
        self.ui_verticalLayout_scale_1.addWidget(self.ui_sb_image_scale_min)
        self.ui_verticalLayout_scale_2 = QtWidgets.QVBoxLayout()
        self.ui_verticalLayout_scale_2.addWidget(self.ui_vs_image_scale_upper)
        self.ui_verticalLayout_scale_2.addWidget(self.ui_vs_image_scale_lower)        
        self.ui_horizontalLayout_scale_2 = QtWidgets.QHBoxLayout()
        self.ui_horizontalLayout_scale_2.addLayout(self.ui_verticalLayout_scale_2)
        self.ui_horizontalLayout_scale_2.addLayout(self.ui_verticalLayout_scale_1)
        
        
        self.ui_verticalLayout_Right_Top = QtWidgets.QVBoxLayout()
        self.ui_verticalLayout_Right_Top.addLayout(self.ui_horizontalLayout_scale_2)
        self.ui_verticalLayout_Right_Top.addWidget(self.ui_lb_img_palette)
        self.ui_verticalLayout_Right_Top.addWidget(self.ui_cb_img_palette_list)
        self.ui_verticalLayout_Right_Top.addWidget(self.ui_lb_img_picked_points)
        self.ui_verticalLayout_Right_Top.addWidget(self.ui_cb_img_pk_pts_palette_list)
        self.ui_verticalLayout_Right_Top.addWidget(self.ui_lw_img_picked_points_list_widgets)
        self.ui_verticalLayout_Right_Top.addWidget(self.ui_pb_img_picked_points_remove)
        
        self.ui_horizontalLayout_Top = QtWidgets.QHBoxLayout()
        self.ui_horizontalLayout_Top.addWidget(self.static_canvas)
        self.ui_horizontalLayout_Top.addLayout(self.ui_verticalLayout_Right_Top)       
        
        # Layout Bottom                         
        self.ui_horizontalLayout_var_name = QtWidgets.QHBoxLayout()
        self.ui_horizontalLayout_image_data_type = QtWidgets.QHBoxLayout()
        self.ui_horizontalLayout_img_layer = QtWidgets.QHBoxLayout()
        self.ui_horizontalLayout_var_name.addWidget(self.ui_lb_selected_var_name)
        self.ui_horizontalLayout_var_name.addWidget(self.ui_le_selected_var)
        self.ui_horizontalLayout_image_data_type.addWidget(self.ui_le_image_data_type)
        self.ui_horizontalLayout_image_data_type.addWidget(self.ui_cb_image_data_type)
        self.ui_horizontalLayout_img_layer.addWidget(self.ui_lb_image_layer)
        self.ui_horizontalLayout_img_layer.addWidget(self.ui_sb_image_layers)
        self.ui_horizontalLayout_img_layer.addWidget(self.ui_le_layer_value)
        
        self.ui_verticalLayout_Left_Bottom = QtWidgets.QVBoxLayout() 
        self.ui_verticalLayout_Left_Bottom.addWidget(self.ui_pb_select_var)        
        self.ui_verticalLayout_Left_Bottom.addLayout(self.ui_horizontalLayout_var_name)
        self.ui_verticalLayout_Left_Bottom.addLayout(self.ui_horizontalLayout_image_data_type)
        self.ui_verticalLayout_Left_Bottom.addLayout(self.ui_horizontalLayout_img_layer)
        
        self.ui_verticalLayout_Right_Bottom = QtWidgets.QVBoxLayout() 
        self.ui_verticalLayout_Right_Bottom.addWidget(self.ui_lb_img_to_data_coord)
        self.ui_verticalLayout_Right_Bottom.addWidget(self.ui_le_img_to_data_coordinate)
        self.ui_verticalLayout_Right_Bottom.addWidget(self.ui_lb_uds_data_info)
        self.ui_verticalLayout_Right_Bottom.addWidget(self.ui_lw_uds_data_info)
        
        self.ui_horizontalLayout_Bottom = QtWidgets.QHBoxLayout()        
        self.ui_horizontalLayout_Bottom.addLayout(self.ui_verticalLayout_Left_Bottom)
        self.ui_horizontalLayout_Bottom.addLayout(self.ui_verticalLayout_Right_Bottom)

        # Layout       
        self.ui_verticalLayout = QtWidgets.QVBoxLayout()
        self.ui_verticalLayout.setContentsMargins(0,0,0,0) # left, top, right, bottom
        self.ui_verticalLayout.addWidget(self.ui_lb_widget_name)
        self.ui_verticalLayout.addLayout(self.ui_horizontalLayout_Top)
        self.ui_verticalLayout.addWidget(self.ui_lb_img_proc_parameter)
        self.ui_verticalLayout.addWidget(self.ui_le_img_proc_parameter_list)
        self.ui_verticalLayout.addLayout(self.ui_horizontalLayout_Bottom)
        
        self.ui_gridlayout = QtWidgets.QGridLayout()
        self.ui_gridlayout.addLayout(self.ui_verticalLayout, 0, 0, 1, 1)
        self.ui_gridlayout.setContentsMargins(0,0,0,0) # left, top, right, bottom
        
        self.setLayout(self.ui_gridlayout)        
        
    def initNonUiMembers(self):
        
        # Var
        self.uds_variable = 0
        self.selected_var_name = ''
        
        self.uds_varibale_type = ''
        
        self.uds_varibale_dataCopy = 0
        self.uds_variable_dataAcCopy = 0
        
        self.uds_var_layer_value = []
        
        #  Msg Type
        self.msg_type = []
        self.msg_type.append('SELECT_USD_VARIABLE')
        
        # 
        self.st_img_xlim_l = 0
        self.st_img_xlim_u = 199
        
        self.st_img_ylim_l = 0
        self.st_img_ylim_u = 199
        
        self.st_img_scale_ratio = 1
        
        self.selected_data_pt_x = 0
        self.selected_data_pt_y = 0

        self.img_picked_points_list = []
        
        self.img_current_layer = 0
        
        self.zoom_direction = 0
        
        self.mouse_left_button_released = True
        self.mouse_right_button_released = True
        
        self.mouse_cord_x = 0
        self.mouse_cord_y = 0
        
        # Var data type
        self.var_data_type_list = ['Abs','Angle','Real','Image']
        
        # Color maps
        self.img_color_map_list = ['viridis','plasma','inferno','cividis','PuBu','Purples']
        
        
        self.img_marker_cv_list = ['#ff0000','#00ff00','#0000ff','#000000','#ffffff']
        self.img_marker_cn_list = ['Red','Green','Blue','Black','White']
        
    """ @SLOTS of UI Widgets"""  
    # Send MSG
    def sendMsgSignalEmit(self, msgTypeIndex):
        self.sendMsgSignal.emit(msgTypeIndex)
        
    def selectVar(self):
        self.sendMsgSignalEmit(self.msg_type.index('SELECT_USD_VARIABLE'))        
        
    #
    def imageDataTypeChanged(self):
        if self.ui_cb_image_data_type.currentIndex() == 0: #Abs
            self.uds_varibale_dataCopy = np.abs(self.uds_variable.data)
        elif self.ui_cb_image_data_type.currentIndex() == 1: #Angle
            self.uds_varibale_dataCopy = np.angle(self.uds_variable.data)
        elif self.ui_cb_image_data_type.currentIndex() == 2: #Real
            self.uds_varibale_dataCopy = np.real(self.uds_variable.data)
        elif self.ui_cb_image_data_type.currentIndex() == 3: #Image
            self.uds_varibale_dataCopy = np.imag(self.uds_variable.data)
        else:
            print("Error display data type!")
            
        self.uds_variable_dataAcCopy = self.uds_varibale_dataCopy.copy()
        if self.uds_varibale_type == 'fft':
            Ox = int( (self.uds_variable.data.shape[-1] - self.uds_variable.data.shape[-1]%2)/2 )
            Oy = int( (self.uds_variable.data.shape[-2] - self.uds_variable.data.shape[-2]%2)/2 )
            self.uds_variable_dataAcCopy[:,Oy,Ox] = np.zeros(self.uds_variable.data.shape[-0])
        
        self.imageLayerChanged()
        
    def imgeScaleChanged(self):
        self.img_current_layer = self.ui_sb_image_layers.value()
        
        self.updateImage()
        
    def imageLayerChanged(self):        
        self.ui_sb_image_scale_max.valueChanged.disconnect()               
        self.ui_sb_image_scale_min.valueChanged.disconnect()
        
        self.img_current_layer = self.ui_sb_image_layers.value()
        if len(self.uds_var_layer_value) > 0:
            self.ui_le_layer_value.setText(str(self.uds_var_layer_value[self.img_current_layer]))
        
        if self.uds_varibale_type == 'fft':
            layer_data_minimum = np.min(self.uds_variable_dataAcCopy [self.img_current_layer, :, :])
            layer_data_maximum = np.max(self.uds_variable_dataAcCopy[self.img_current_layer, :, :])
        else:
            layer_data_minimum = np.min(self.uds_varibale_dataCopy[self.img_current_layer, :, :])
            layer_data_maximum = np.max(self.uds_varibale_dataCopy[self.img_current_layer, :, :])
        
        self.ui_sb_image_scale_min.setMinimum(layer_data_minimum)
        self.ui_sb_image_scale_min.setMaximum (layer_data_maximum)
        
        self.ui_sb_image_scale_max.setMinimum(layer_data_minimum)
        self.ui_sb_image_scale_max.setMaximum (layer_data_maximum)
        
        self.ui_sb_image_scale_min.setValue(layer_data_minimum )
        self.ui_sb_image_scale_max.setValue(layer_data_maximum )
        
        self.updateImage()
        
        self.ui_sb_image_scale_max.valueChanged.connect(self.imgeScaleChanged)                
        self.ui_sb_image_scale_min.valueChanged.connect(self.imgeScaleChanged)
        
        
    def imageColorMapChanged(self):
        self.updateImage()
        
    def imageMarkerColorChanged(self):
        self.updateImage()
        
    def removePickedPoint(self):
        current_idx = self.ui_lw_img_picked_points_list_widgets.currentRow()
        
        if current_idx >= 0:
            self.img_picked_points_list.pop(current_idx)
            self.ui_lw_img_picked_points_list_widgets.clear()
            self.ui_lw_img_picked_points_list_widgets.addItems(self.img_picked_points_list)
            if current_idx == len(self.img_picked_points_list):
                current_idx = len(self.img_picked_points_list) - 1
            self.ui_lw_img_picked_points_list_widgets.setCurrentRow(current_idx)            
            
            self.updateImage()
        
    """ @SLOTS of Mouse Event"""
    def canvasMouseMoveEvent(self, event):
        self.ui_le_img_to_data_coordinate.clear()
        
        if self.mouse_left_button_released == True:
            self.canvasSelectedPixToDataPix(event.x(), event.y())
            
            s_pt_x = int(self.selected_data_pt_x)
            s_pt_y = int(self.selected_data_pt_y)
            
            d_r = self.uds_variable.data.shape[-2]
            d_c = self.uds_variable.data.shape[-1]
            
            if s_pt_x >= 0 and s_pt_x < d_c and s_pt_y >= 0 and s_pt_y < d_r :
                self.ui_le_img_to_data_coordinate.setText('Z( %d : %d ) = %f' % 
                                                     (self.selected_data_pt_x,self.selected_data_pt_y,
                                                      self.uds_varibale_dataCopy[self.img_current_layer, int(s_pt_y), int(s_pt_x)]))
            else:
                self.ui_le_img_to_data_coordinate.setText('( %d : %d )' % (self.selected_data_pt_x,self.selected_data_pt_y))
        else:
            self.canvasSelectedPixToDataPix(event.x(), event.y())
            
            current_mouse_x = int(event.x())
            current_mouse_y = int(event.y())
            
            dx = int((current_mouse_x - self.mouse_cord_x)/self.st_img_scale_ratio)
            dy = int((current_mouse_y - self.mouse_cord_y)/self.st_img_scale_ratio)
            
            self.st_img_xlim_l -= dx
            self.st_img_xlim_u -= dx
                   
            self.st_img_ylim_l -= dy
            self.st_img_ylim_u -= dy
            
            self.updateImage() 
            
            #
            self.mouse_cord_x = current_mouse_x
            self.mouse_cord_y = current_mouse_y
            
    def canvasMousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.canvasSelectedPixToDataPix(event.x(), event.y())
            
            self.img_picked_points_list.append('%d,%d' % (self.selected_data_pt_x,self.selected_data_pt_y))
            self.ui_lw_img_picked_points_list_widgets.clear()
            self.ui_lw_img_picked_points_list_widgets.addItems(self.img_picked_points_list)
            self.ui_lw_img_picked_points_list_widgets.setCurrentRow(len(self.img_picked_points_list)-1)
            
            self.updateImage()
            
            self.mouse_right_button_released = False
            
        elif event.button() == QtCore.Qt.LeftButton:
            self.canvasSelectedPixToDataPix(event.x(), event.y())
            
            self.mouse_cord_x = int(event.x())
            self.mouse_cord_y = int(event.y())
            
            self.mouse_left_button_released = False
            
    def canvasMouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.mouse_right_button_released = True
        elif event.button() == QtCore.Qt.LeftButton:
            self.mouse_left_button_released = True
        
    def canvasWheelEvent(self, event):        
        self.canvasSelectedPixToDataPix(event.x(), event.y())
        
        self.zoom_direction += event.angleDelta().y()
        
        var_shape = np.shape(self.uds_variable.data)
        
        if abs(self.zoom_direction) > 110: 
            if self.zoom_direction >0: # Zoom in

                self.st_img_scale_ratio *= 2
                x_lim_l_ = self.st_img_xlim_l + (self.st_img_xlim_u - self.st_img_xlim_l)/4  
                x_lim_l_ -= (self.st_img_xlim_u + self.st_img_xlim_l)/4 - self.selected_data_pt_x/2            
                x_lim_u_ = x_lim_l_ + (self.st_img_xlim_u - self.st_img_xlim_l)/2
                self.st_img_xlim_l = x_lim_l_
                self.st_img_xlim_u = x_lim_u_
                
                y_lim_l_ = self.st_img_ylim_l + (self.st_img_ylim_u - self.st_img_ylim_l)/4  
                y_lim_l_ -= (self.st_img_ylim_u + self.st_img_ylim_l)/4 - self.selected_data_pt_y/2            
                y_lim_u_ = y_lim_l_ + (self.st_img_ylim_u - self.st_img_ylim_l)/2
                self.st_img_ylim_l = y_lim_l_
                self.st_img_ylim_u = y_lim_u_
                
            else: #Zoom out
                if self.st_img_scale_ratio > 2:
                    self.st_img_scale_ratio /= 2
                    x_lim_l_ = self.st_img_xlim_l - (self.st_img_xlim_u - self.st_img_xlim_l)/2  
                    x_lim_l_ += (self.st_img_xlim_u + self.st_img_xlim_l)/2 - self.selected_data_pt_x
                    x_lim_u_ = x_lim_l_ + (self.st_img_xlim_u - self.st_img_xlim_l)*2
                    self.st_img_xlim_l = x_lim_l_
                    self.st_img_xlim_u = x_lim_u_
                    
                    y_lim_l_ = self.st_img_ylim_l - (self.st_img_ylim_u - self.st_img_ylim_l)/2 
                    y_lim_l_ += (self.st_img_ylim_u + self.st_img_ylim_l)/2 - self.selected_data_pt_y
                    y_lim_u_ = y_lim_l_ + (self.st_img_ylim_u - self.st_img_ylim_l)*2
                    self.st_img_ylim_l = y_lim_l_
                    self.st_img_ylim_u = y_lim_u_
                    
                else:
                   self.st_img_scale_ratio = 1
                   var_shape = np.shape(self.uds_variable.data)
                   
                   self.st_img_xlim_l = 0
                   self.st_img_xlim_u = var_shape[-1]
                   
                   self.st_img_ylim_l = 0
                   self.st_img_ylim_u = var_shape[-2]
            self.zoom_direction = 0        
        
        self.updateImage()     

    """ Regular Functions """        
    def setCanvasWidgetSize(self, w, h):
        self.static_canvas.setFixedWidth(w)
        self.static_canvas.setFixedHeight(h)
               
    def setUdsData(self, usd_variable):
        self.selected_var_name = usd_variable.name
        self.uds_variable = usd_variable
        self.uds_varibale_dataCopy = np.abs(self.uds_variable.data)
        self.uds_varibale_type = usd_variable.name.split('_')[-1]
        
        #
        if self.uds_varibale_type == 'fft':
            Ox = int( (self.uds_variable.data.shape[-1] - self.uds_variable.data.shape[-1]%2)/2 )
            Oy = int( (self.uds_variable.data.shape[-2] - self.uds_variable.data.shape[-2]%2)/2 )
            self.uds_variable_dataAcCopy = self.uds_varibale_dataCopy.copy()
            self.uds_variable_dataAcCopy[:,Oy,Ox] = np.zeros(self.uds_variable.data.shape[-0])
            
        #
        self.ui_le_selected_var.setText(self.selected_var_name)
        
        #
        self.ui_le_layer_value.setText('')
        
        #
        var_shape = np.shape(self.uds_variable.data)
        self.uds_var_layer_value = []        
        if len(var_shape) < 3:            
            print("error data shape")       
        else:       
            self.ui_sb_image_layers.setMinimum(0)
            self.ui_sb_image_layers.setMaximum(var_shape[0]-1)         
            #
            if 'LayerValue' in self.uds_variable.info:
                self.uds_var_layer_value = self.uds_variable.info['LayerValue'].copy()
                        
        #
        self.ui_sb_image_scale_min.setSingleStep(0.01)
        self.ui_sb_image_scale_max.setSingleStep(0.01)
        
        self.st_img_xlim_l = 0
        self.st_img_xlim_u = var_shape[-1]
        
        self.st_img_ylim_l = 0
        self.st_img_ylim_u = var_shape[-2]
        
        self.st_img_scale_ratio = 1
        
        #
        if self.ui_sb_image_layers.value() == 0:
            self.imageLayerChanged()
        else:
            self.ui_sb_image_layers.setValue(0)
            
        if not self.uds_varibale_type == 'fft':
            if self.ui_cb_image_data_type.currentIndex() == 2: #real
                self.imageDataTypeChanged()
            else:
                self.ui_cb_image_data_type.setCurrentIndex(2) #real

        self.ui_sb_image_layers.setEnabled(True)
        
        self.ui_cb_image_data_type.setEnabled(True)
        
        self.static_canvas.setEnabled(True)
        
        self.updateDataInfo()
    
    def updateDataInfo(self):
        self.ui_lw_uds_data_info.clear()
        for i in self.uds_variable.info:
            self.ui_lw_uds_data_info.addItem('%s:%s' % (i,self.uds_variable.info[i]))
        
    def updateImage(self):
        scale_min = self.ui_sb_image_scale_min.value()
        scale_max = self.ui_sb_image_scale_max.value()
        
        color_map = self.ui_cb_img_palette_list.currentText()
        mk_color_idx = self.ui_cb_img_pk_pts_palette_list.currentIndex()
        mk_color_nm = self.img_marker_cv_list[mk_color_idx]
        
        self.static_ax.clear()
        
        # plot data
        self.static_ax.imshow(self.uds_varibale_dataCopy[self.img_current_layer, :, :], vmin = scale_min, vmax = scale_max, 
                              cmap= color_map,interpolation = 'nearest',aspect = 'auto')
        self.static_ax.set(xlim=(self.st_img_xlim_l,self.st_img_xlim_u),ylim=(self.st_img_ylim_u,self.st_img_ylim_l))
        self.static_ax.axis('off')
        self.static_ax.get_xaxis().set_visible(False)
        self.static_ax.get_yaxis().set_visible(False)
        self.static_ax.set_frame_on(False)
        
        # plot markers        
        pt_len = len(self.img_picked_points_list)
        if pt_len > 0:
            mk_x = []
            mk_y = []
            for i in range(pt_len):
                mk_x.append(int(self.img_picked_points_list[i].split(',')[0]))
                mk_y.append(int(self.img_picked_points_list[i].split(',')[1]))
            self.static_ax.scatter(mk_x, mk_y, s=200, c=mk_color_nm, marker='x')

        self.static_ax.figure.canvas.draw()
               
    def canvasSelectedPixToDataPix(self, canvas_x, canvas_y):
        canvas_w = self.static_canvas.getWidgetWidth()
        canvas_h = self.static_canvas.getWidgetHeight()
        
        x_ratio = ( canvas_x + 1) / canvas_w 
        y_ratio = ( canvas_y + 1) / canvas_h
        
        self.selected_data_pt_x = round(x_ratio * (self.st_img_xlim_u - self.st_img_xlim_l ) + self.st_img_xlim_l )
        self.selected_data_pt_y = round(y_ratio * (self.st_img_ylim_u - self.st_img_ylim_l ) + self.st_img_ylim_l )
        

        