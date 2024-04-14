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
from PyQt5.QtCore import Qt

"""
User Modules
"""
from .customizedWidgets.RangeSlider import RangeSlider

""" *************************************** """
""" DO NOT MODIFY THIS FILE"""
""" *************************************** """

class ScaleWidget(QtWidgets.QWidget):
    
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super(ScaleWidget, self).__init__(parent)
        
        self.initNonUiMembers(orientation)        
        self.initUiMembers()
        self.initUiLayout()
        
    def initNonUiMembers(self, orientation):
        self.orientation = orientation
        self.slider_max = 1000
        self.slider_min = 0
        self.data_max = 0
        self.data_min = 0
        self.data_upper_value = 0
        self.data_lower_value = 0
        self.data_sigma_factor = 3
        self.data = 0
    
    def initUiMembers(self):
        self.rangeSlider = RangeSlider(self.orientation)
        self.le_data_upper_value = QtWidgets.QLineEdit()
        self.le_data_lower_value = QtWidgets.QLineEdit()
        self.le_data_sigma_factor = QtWidgets.QLineEdit()
        self.lb_sigma = QtWidgets.QLabel('σ')
    
    def initUiLayout(self):
        if self.orientation == Qt.Horizontal:
            pass
        else:
            ui_v_horiztontalLayout1 = QtWidgets.QHBoxLayout()
            ui_v_horiztontalLayout1.addWidget(self.lb_sigma)
            ui_v_horiztontalLayout1.addWidget(self.le_data_sigma_factor)
            ui_v_vertialLayout1 = QtWidgets.QVBoxLayout()
            ui_v_vertialLayout1.addWidget(self.le_data_upper_value)
            ui_v_vertialLayout1.addLayout(ui_v_horiztontalLayout1)
            ui_v_vertialLayout1.addWidget(self.le_data_lower_value)
            ui_v_horiztontalLayout2 = QtWidgets.QHBoxLayout()
            ui_v_horiztontalLayout2.addWidget(self.rangeSlider)
            ui_v_horiztontalLayout2.addLayout(ui_v_vertialLayout1)
            
            ui_gridlayout = QtWidgets.QGridLayout()
            ui_gridlayout.addLayout(ui_v_horiztontalLayout2, 0, 0, 1, 1)
            #ui_gridlayout.setContentsMargins(0,0,0,0) # left, top, right, bottom
            
        self.setLayout(ui_gridlayout)
            