# -*- coding: utf-8 -*-
"""
Created on Tue May 21 17:19:04 2024

@author: jiahao
"""

"""
System modules
"""

"""
Third-party Modules
"""
import numpy as np
from io import BytesIO
from PyQt5 import QtCore, QtWidgets, QtGui

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure
"""
User Modules
"""

from .GuiFrame import GuiFrame
from .Plot1Uds2Widget import Plot1Uds2Widget
from .ConfigManager import ConfigManager


""" *************************************** """
""" DO NOT MODIFY THE REGION UNTIL INDICATED"""
""" *************************************** """

class Plot1Uds2(GuiFrame):
    
    def __init__(self, wtype, index, *args, **kwargs):
        super(Plot1Uds2, self).__init__(wtype, index, *args, **kwargs)        
        
        self.initCcUiMembers()
        self.initCcUiLayout()        
        self.initCcNonUiMembers()        
        self.initCcMenuBar()
        
        self.initPreference()
        
    """ Initializations"""
    def initPreference(self):
        pass
    
    def initCcUiMembers(self):  
        self.ui_plot_widget = Plot1Uds2Widget()
        
        #
        self.ui_lw_uds_variable_name_list.doubleClicked.connect(self.ui_lw_uds_variable_name_list_doulbeClicked)
        
    def initCcUiLayout(self):
        self.ui_horizontalLayout.addWidget(self.ui_plot_widget)
        
    def initCcNonUiMembers(self):
        # Settings
        self.settings = self.loadSettings()
        
        #
        self.sync_pick_points = False
        self.sync_rt_points = False
        self.sync_canvas_zoom = False
        
        #
        self.canvas_size_factor = 0.33
        
    def initCcMenuBar(self):
        pass

    """ Settings """
    def loadSettings(self):
        return ConfigManager.load_settings_from_file('./ScienceY/config/ImageUdsData2or3D.txt')
    
    def saveSettings(self):
        ConfigManager.save_settings_to_file('./ScienceY/config/ImageUdsData2or3D.txt', self.settings)

    """ @SLOTS of UI Widgets"""

    #
    def ui_lw_uds_variable_name_list_doulbeClicked(self):
        #self.getMsgFromImgMainWidget(self.ui_img_widget_main.msg_type.index('SELECT_USD_VARIABLE'))
        selected_var_index = self.ui_lw_uds_variable_name_list.currentRow()
        selected_var = self.uds_variable_pt_list[selected_var_index]        

        self.ui_plot_widget.setUdsData(selected_var)
        
  