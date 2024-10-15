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
from .PlotConfigWidget import PlotConfigWidget
from .ConfigManager import ConfigManager
from .customizedWidgets.DockWidget import DockWidget

""" *************************************** """
""" DO NOT MODIFY THE REGION UNTIL INDICATED"""
""" *************************************** """

class VarTreeWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # Example data: 2D NumPy arrays for each variable
        self.uds_data_list = []

        # Set up the tree widget
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Var Name"])
        self.tree.itemChanged.connect(self.on_item_changed)

        # Set up the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)

    def setUdsData(self, uds_data, method='New'):
        if method == 'New':
            self.uds_data_list.clear()
            self.uds_data_list.append(uds_data)
            self.setup_tree()
        elif method == 'Add':
            self.uds_data_list.append(uds_data)
            self.setup_tree()
        else:
            print('Unknown setUdsData Method')
                
    def setup_tree(self):
        """Add variables and rows with checkboxes to the tree widget."""
        self.tree.clear()
        for uds_data in self.uds_data_list:
            # Create a top-level item for each variable
            var_item = QtWidgets.QTreeWidgetItem([uds_data.name])
            self.tree.addTopLevelItem(var_item)

            # Add each row of the array as a child item with a checkbox
            for i in range(uds_data.data.shape[0]):
                row_item = QtWidgets.QTreeWidgetItem([f"Line {i}"])
                row_item.setCheckState(0, 0)  # 0 = Unchecked, 2 = Checked
                var_item.addChild(row_item)
                
    def on_item_changed(self, item, column):
        if item.checkState(0) == 2:  # 2 means 'Checked'
            print(f"{item.text(0)} is checked.")
        else:
            print(f"{item.text(0)} is unchecked.")

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
        self.ui_var_plotted_widget = VarTreeWidget()
        self.ui_pb_select_all_lines = QtWidgets.QPushButton('Select All Lines')
        self.ui_pb_unselect_all_lines = QtWidgets.QPushButton('Unselect All Lines')
        self.ui_pb_add_var_to_plot = QtWidgets.QPushButton('Add to plot')
        self.ui_pb_add_var_to_plot.clicked.connect(self.ui_pb_add_var_to_plot_clicked)
        self.ui_pb_remove_var_from_plot = QtWidgets.QPushButton('Remove from plot')
        self.ui_lb_line_proc_parameter = QtWidgets.QLabel("Params (p1,p2,...): ")
        self.ui_le_line_proc_parameter_list = QtWidgets.QLineEdit()
        
        #
        self.ui_dockWidget_plot_config = DockWidget('Plot Config')
        self.ui_dockWidget_plot_config_content = PlotConfigWidget()
        #self.ui_dockWidget_fs_tree_content.selectionChangedSignal.connect(self.fileTreeSelectionChanged)
        
        
        #
        self.ui_lw_uds_variable_name_list.doubleClicked.connect(self.ui_lw_uds_variable_name_list_doulbeClicked)
        
    def initCcUiLayout(self):
        ui_vLayout1 = QtWidgets.QVBoxLayout()
        ui_vLayout1.addWidget(self.ui_var_plotted_widget)
        
        ui_hLayout2 = QtWidgets.QHBoxLayout()
        ui_hLayout2.addWidget(self.ui_pb_select_all_lines)
        ui_hLayout2.addWidget(self.ui_pb_unselect_all_lines)
        ui_vLayout1.addLayout(ui_hLayout2)
        
        ui_hLayout3 = QtWidgets.QHBoxLayout()
        ui_hLayout3.addWidget(self.ui_pb_add_var_to_plot)
        ui_hLayout3.addWidget(self.ui_pb_remove_var_from_plot)
        ui_vLayout1.addLayout(ui_hLayout3)
        
        ui_vLayout2 = QtWidgets.QVBoxLayout()
        ui_vLayout2.addWidget(self.ui_lb_line_proc_parameter)
        ui_vLayout2.addWidget(self.ui_le_line_proc_parameter_list)
        ui_vLayout1.addLayout(ui_vLayout2)
        
        self.ui_horizontalLayout.addLayout(ui_vLayout1)        
        self.ui_horizontalLayout.addWidget(self.ui_plot_widget)
        
        #dock widget
        self.ui_dockWidget_plot_config.setWidget(self.ui_dockWidget_plot_config_content)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea , self.ui_dockWidget_plot_config)
        
        self.tabifyDockWidget(self.ui_dockWideget_var, self.ui_dockWidget_plot_config)
        
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
    def resizeEvent(self, event):                      
        screens = QtWidgets.QApplication.screens()                
        for s in screens:
            if s == QtWidgets.QApplication.screenAt(self.pos()):                
                width = int( 0.5 * (s.size().width() + s.size().height())/2/16)*16
                height = width
                self.ui_plot_widget.setCanvasWidgetSize(width, height)
                self.ui_var_plotted_widget.setFixedWidth(int(width*0.5))
          
    #
    def ui_lw_uds_variable_name_list_doulbeClicked(self):
        #self.getMsgFromImgMainWidget(self.ui_img_widget_main.msg_type.index('SELECT_USD_VARIABLE'))
        selected_var_index = self.ui_lw_uds_variable_name_list.currentRow()
        selected_var = self.uds_variable_pt_list[selected_var_index]        

        self.ui_plot_widget.setUdsData(selected_var)
        self.ui_var_plotted_widget.setUdsData(selected_var)
        
    def ui_pb_add_var_to_plot_clicked(self):
        selected_var_index = self.ui_lw_uds_variable_name_list.currentRow()
        selected_var = self.uds_variable_pt_list[selected_var_index]
        
        self.ui_var_plotted_widget.setUdsData(selected_var, 'Add')
        
    def ui_pb_remove_var_from_plot_clicked(self):
        pass
        
  