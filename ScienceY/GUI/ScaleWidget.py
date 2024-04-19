# -*- coding: utf-8 -*-
"""
Created on Tue Apr  9 16:04:58 2024

@author: Jiahao Yan
"""

"""
System modules
"""

"""
Third-party Modules
"""
import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal

"""
User Modules
"""
from .customizedWidgets.RangeSlider import RangeSlider
from .customizedWidgets.SimplifiedNumberLineEditor import SimplifiedNumberLineEditor
from .general.NumberExpression import NumberExpression

""" *************************************** """
""" DO NOT MODIFY THIS FILE"""
""" *************************************** """

class ScaleWidget(QtWidgets.QWidget):
    scaleChanged = pyqtSignal()  # Signal for value change
    
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super(ScaleWidget, self).__init__(parent)
        
        self.initNonUiMembers(orientation)        
        self.initUiMembers()
        self.initUiLayout()
        
    def initNonUiMembers(self, orientation):
        self.orientation = orientation
        self.slider_max = 1000
        self.slider_min = 0
        self.slider_upper_value = self.slider_max
        self.slider_lower_value = self.slider_min
        
        self.data_max = 0.0
        self.data_min = 0.0
        self.data_upper_limit = 0.0
        self.data_lower_limit = 0.0
        self.data_upper_value = 0.0
        self.data_lower_value = 0.0
        self.zoom_out_factor = 0.2
        self.zoom_in_factor = 0.8
        self.data_scale_fixed = False
        
        self.data_sigma_factor = 4.5
        self.data_sigma_factor_default = 4.5
        self.data = 0
        
        self.indicator_upper_value = 0.0
        self.indicator_lower_value = 0.0
        
        self.auto_scale_strategy = ''
        self.auto_scale_fft_factor = 1.0
    
    def initUiMembers(self):
        self.ui_rangeSlider = RangeSlider(self.orientation)
        self.ui_rangeSlider.setRange(self.slider_min, self.slider_max)
        self.ui_rangeSlider.valueChanged.connect(self.sliderMoved)
        self.ui_le_data_upper_value = SimplifiedNumberLineEditor()
        self.ui_le_data_upper_value.validTextChanged.connect(self.dataUpperValueChange)
        self.ui_le_data_lower_value = SimplifiedNumberLineEditor()
        self.ui_le_data_lower_value.validTextChanged.connect(self.dataLowerValueChanged)
        self.ui_le_data_sigma_factor = SimplifiedNumberLineEditor()
        self.ui_le_data_sigma_factor.setSNText(str(self.data_sigma_factor))
        self.ui_le_data_sigma_factor.validTextChanged.connect(self.sigmaFactorChanged)
        self.ui_lb_sigma = QtWidgets.QLabel('σ')
        
        self.ui_pb_scale_full__sigma = QtWidgets.QPushButton('F')
        self.ui_pb_scale_full__sigma.clicked.connect(self.fullScale)
        self.ui_pb_scale_full__sigma.setMaximumSize(40,40)
        self.ui_pb_scale_zoom_in = QtWidgets.QPushButton('i')
        self.ui_pb_scale_zoom_in.clicked.connect(self.zoomInScale)
        self.ui_pb_scale_zoom_in.setMaximumSize(40,40)
        self.ui_pb_scale_zoom_out = QtWidgets.QPushButton('o')
        self.ui_pb_scale_zoom_out.clicked.connect(self.zoomOutScale)
        self.ui_pb_scale_zoom_out.setMaximumSize(40,40)
    
    def initUiLayout(self):
        if self.orientation == Qt.Horizontal:
            ui_h_horiztontalLayout1 = QtWidgets.QHBoxLayout()
            ui_h_horiztontalLayout1.addWidget(self.ui_pb_scale_full__sigma)
            ui_h_horiztontalLayout1.addWidget(self.ui_pb_scale_zoom_out)
            ui_h_horiztontalLayout1.addWidget(self.ui_pb_scale_zoom_in)
            ui_h_verticalLayout1 = QtWidgets.QVBoxLayout()            
            ui_h_verticalLayout1.addWidget(self.ui_le_data_sigma_factor)
            ui_h_verticalLayout1.addWidget(self.ui_lb_sigma)
            self.ui_lb_sigma.setAlignment(Qt.AlignCenter)
            ui_h_horiztontalLayout2 = QtWidgets.QHBoxLayout()
            ui_h_horiztontalLayout2.addWidget(self.ui_le_data_lower_value)
            ui_h_horiztontalLayout2.addLayout(ui_h_verticalLayout1)
            ui_h_horiztontalLayout2.addWidget(self.ui_le_data_upper_value)
            ui_h_verticalLayout2 = QtWidgets.QVBoxLayout()
            ui_h_verticalLayout2.addLayout(ui_h_horiztontalLayout1)
            ui_h_verticalLayout2.addWidget(self.ui_rangeSlider)
            ui_h_verticalLayout2.addLayout(ui_h_horiztontalLayout2)
            
            ui_gridlayout = QtWidgets.QGridLayout()
            ui_gridlayout.addLayout(ui_h_verticalLayout2, 0, 0, 1, 1)

        else:
            ui_v_horiztontalLayout1 = QtWidgets.QHBoxLayout()
            ui_v_horiztontalLayout1.addWidget(self.ui_lb_sigma)
            ui_v_horiztontalLayout1.addWidget(self.ui_le_data_sigma_factor)
            ui_v_vertialLayout1 = QtWidgets.QVBoxLayout()
            ui_v_vertialLayout1.addWidget(self.ui_le_data_upper_value)
            ui_v_vertialLayout1.addLayout(ui_v_horiztontalLayout1)
            ui_v_vertialLayout1.addWidget(self.ui_le_data_lower_value)
            ui_v_vertialLayout2 = QtWidgets.QVBoxLayout()
            ui_v_vertialLayout2.addWidget(self.ui_pb_scale_full__sigma)
            ui_v_vertialLayout2.addWidget(self.ui_pb_scale_zoom_out)
            ui_v_vertialLayout2.addWidget(self.ui_pb_scale_zoom_in)
            ui_v_horiztontalLayout2 = QtWidgets.QHBoxLayout()
            ui_v_horiztontalLayout2.addLayout(ui_v_vertialLayout2)
            ui_v_horiztontalLayout2.addWidget(self.ui_rangeSlider)
            ui_v_horiztontalLayout2.addLayout(ui_v_vertialLayout1)
            
            ui_gridlayout = QtWidgets.QGridLayout()
            ui_gridlayout.addLayout(ui_v_horiztontalLayout2, 0, 0, 1, 1)
            #ui_gridlayout.setContentsMargins(0,0,0,0) # left, top, right, bottom
            
        self.setLayout(ui_gridlayout)
        
    """ @SLOTS """
    def sliderMoved(self, s_lowerV, s_upperV):
        s_min = self.slider_min
        s_max = self.slider_max
        
        d_l_l = self.data_lower_limit
        d_u_l = self.data_upper_limit
        
        d_l_v = s_lowerV / (s_max - s_min) * (d_u_l - d_l_l) + d_l_l
        d_u_v = s_upperV / (s_max - s_min) * (d_u_l - d_l_l) + d_l_l
        
        self.data_lower_value = d_l_v
        self.data_upper_value = d_u_v
        
        self.scaleChanged.emit()
        
        self.setIndicators(d_l_v, d_u_v)
        
    def sigmaFactorChanged(self):
        sigma = NumberExpression.simplified_number_to_float(self.ui_le_data_sigma_factor.text())
        self.setSigma(sigma)
        
        self.scaleChanged.emit()
    
    def dataLowerValueChanged(self):
        idc_l_v = NumberExpression.simplified_number_to_float(self.ui_le_data_lower_value.snText())
        if idc_l_v >= self.data_upper_value :
            snt = NumberExpression().float_to_simplified_number(self.data_lower_value)
            self.ui_le_data_lower_value.setSNText(snt)
        elif idc_l_v < self.data_lower_limit:
            self.data_lower_limit = idc_l_v
            self.data_lower_value = idc_l_v
            
            self.dataValueChanged()
        else:
            self.data_lower_value = idc_l_v
            self.dataValueChanged()
            
    def dataUpperValueChange(self):
        idc_u_v = NumberExpression.simplified_number_to_float(self.ui_le_data_upper_value.snText())
        if idc_u_v <= self.data_lower_value :
            snt = NumberExpression().float_to_simplified_number(self.data_upper_value)
            self.ui_le_data_upper_value.setSNText(snt)
        elif idc_u_v > self.data_upper_limit:
            self.data_upper_limit = idc_u_v
            self.data_upper_value = idc_u_v
            
            self.dataValueChanged()
        else:
            self.data_upper_value = idc_u_v
            self.dataValueChanged()
    
    def fullScale(self):
        self.data_sigma_factor = self.data_sigma_factor_default
        self.AutoScale()
        self.ui_le_data_sigma_factor.setSNText(str(self.data_sigma_factor))
        
        self.scaleChanged.emit()
    
    def zoomOutScale(self):
        data_limit_range = self.data_upper_limit - self.data_lower_limit
        data_l_diff = data_limit_range / (self.data_lower_value - self.data_lower_limit + 1)
        data_u_diff = data_limit_range / (self.data_upper_limit - self.data_upper_value + 1)
        
        self.data_lower_limit -= data_l_diff * self.zoom_out_factor 
        self.data_upper_limit += data_u_diff * self.zoom_out_factor 
        
        self.setSlierPosition()
        
        self.setIndicators(self.data_lower_value, self.data_upper_value)
        
    
    def zoomInScale(self):
        data_l_diff = self.data_lower_value - self.data_lower_limit
        data_u_diff = self.data_upper_limit - self.data_upper_value
        
        self.data_lower_limit += data_l_diff * self.zoom_in_factor 
        self.data_upper_limit -= data_u_diff * self.zoom_in_factor 
        
        self.setSlierPosition()
        
        self.setIndicators(self.data_lower_value, self.data_upper_value)
        
    """ Functions for scaling"""
    def lowerValue(self):
        return self.data_lower_value
    
    def upperValue(self):
        return self.data_upper_value
    
    def setData(self, data1D, auto_scale_strategy='ASS_NORMAL'):
        self.data = data1D
        self.auto_scale_strategy = auto_scale_strategy
        self.data_max = np.max(self.data)
        self.data_min = np.min(self.data)
        
        self.data_sigma_factor = self.data_sigma_factor_default
        self.ui_le_data_sigma_factor.setSNText(str(self.data_sigma_factor))
        #
        if not self.data_scale_fixed:
            self.AutoScale()
    
    def setZoomFactor(self, zoom_factor):
        if zoom_factor > 0 and zoom_factor < 1:
            self.zoom_in_factor = zoom_factor
            self.zoom_out_factor = 1 - zoom_factor
        else:
            print('SLider Zoom Factor is out of range!')
    
    def setSigmaDefault(self, sigma_default):
        self.data_sigma_factor_default = sigma_default
    
    def setSigma(self,sigma):
        self.data_sigma_factor = sigma
        
        #
        self.AutoScale()
    
    def setFFTAutoScaleFactor(self, fft_auto_scale_factor):
        if fft_auto_scale_factor > 0 and fft_auto_scale_factor < 1:
            self.auto_scale_fft_factor = fft_auto_scale_factor
        else:
            print('FFT Auto Scale Factor is out of range!')
            
    def setDataScaleFixed(self, data_scale_fixed):
        self.data_scale_fixed = data_scale_fixed
        
    def AutoScale(self):
        if self.auto_scale_strategy == 'ASS_NORMAL':
            std = np.std(self.data)
            mean = np.mean(self.data)           
            self.data_lower_limit = mean - self.data_sigma_factor * std/2
            self.data_upper_limit = mean + self.data_sigma_factor * std/2
        elif self.auto_scale_strategy == 'ASS_FFT':
            self.data_lower_limit = min(self.data)
            self.data_upper_limit = max(self.data) * self.auto_scale_fft_factor
        else:
            print("Auto Scale Strategy is unknow")           

        self.data_lower_value = self.data_lower_limit
        self.data_upper_value = self.data_upper_limit
        
        self.setSlierPosition()
        
        self.setIndicators(self.data_lower_value, self.data_upper_value)
    
    def dataValueChanged(self):
        self.setSlierPosition()
        self.scaleChanged.emit()
    
    def setSlierPosition(self):
        d_l_v = self.data_lower_value
        d_u_v = self.data_upper_value
        d_l_l = self.data_lower_limit
        d_u_l = self.data_upper_limit
        
        s_min = self.slider_min
        s_max = self.slider_max
        
        s_l_v = int((d_l_v - d_l_l) / (d_u_l - d_l_l) * (s_max - s_min)) + s_min
        s_u_v = int((d_u_v - d_l_l) / (d_u_l - d_l_l) * (s_max - s_min)) + s_min        
        
        self.ui_rangeSlider.setValue(s_l_v, s_u_v)
        
    def setIndicators(self,d_lower_value, d_upper_value):
        sn_d_l_v = NumberExpression.float_to_simplified_number(d_lower_value)
        sn_d_u_v = NumberExpression.float_to_simplified_number(d_upper_value)
        
        self.ui_le_data_lower_value.setText(sn_d_l_v)
        self.ui_le_data_upper_value.setText(sn_d_u_v)