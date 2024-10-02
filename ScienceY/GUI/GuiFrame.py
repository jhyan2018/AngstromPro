# -*- coding: utf-8 -*-
"""
Created on Fri Jul 28 10:25:04 2023

@author: Jiahao Yan
"""

"""
System modules
"""
import sys, os

"""
Third-party Modules
"""
import numpy as np
from PyQt5 import QtCore, QtWidgets

"""
User Modules
"""

""" *************************************** """
""" DO NOT MODIFY THIS FILE"""
""" *************************************** """

class GuiFrame(QtWidgets.QMainWindow):
    
    sendDataSignal = QtCore.pyqtSignal(str, int)
    
    def __init__(self, wtype, index, *args, **kwargs):
        super(GuiFrame, self).__init__(*args, **kwargs)
        
        self.initUiMembers()
        self.initUiLayout()        
        self.initNonUiMembers(wtype, index)
        
        self.setWindowTitle(self.w_name)

        
    """ Initializations"""
    def initUiMembers(self):
        self.resize(400,200)
        self.ui_lw_uds_variable_name_list = QtWidgets.QListWidget()
        self.ui_lw_uds_variable_name_list.currentRowChanged.connect(self.varNameListRowChanged)
        self.ui_lw_uds_variable_history_list = QtWidgets.QListWidget()
        
        self.ui_lb_uds_variable_list = QtWidgets.QLabel("Local Var List")
        self.ui_pb_remove_local_var =  QtWidgets.QPushButton("Remove Variable ")
        self.ui_pb_remove_local_var.clicked.connect(self.removeFromLocalVarList)
        self.ui_pb_send_var_to_guiMngr =  QtWidgets.QPushButton("<- Send <- ")
        self.ui_pb_send_var_to_guiMngr.clicked.connect(self.sendDataSingalEmit)
        self.ui_lb_uds_variable_history = QtWidgets.QLabel("Process History")
        
    def initUiLayout(self):       
        self.ui_verticalLayout_varList = QtWidgets.QVBoxLayout()
        self.ui_verticalLayout_varList.addWidget(self.ui_lb_uds_variable_list)
        self.ui_verticalLayout_varList.addWidget(self.ui_lw_uds_variable_name_list)
        self.ui_verticalLayout_varList.addWidget(self.ui_pb_remove_local_var)
        self.ui_verticalLayout_varList.addWidget(self.ui_pb_send_var_to_guiMngr)
        self.ui_verticalLayout_varList.addWidget(self.ui_lb_uds_variable_history)
        self.ui_verticalLayout_varList.addWidget(self.ui_lw_uds_variable_history_list)
        
        # dockWiget Var
        self.ui_dockWideget_var = QtWidgets.QDockWidget('Var')
        self.ui_dockWidget_var_Content = QtWidgets.QWidget()
        self.ui_gridLayout_dock_var= QtWidgets.QGridLayout()
        self.ui_gridLayout_dock_var.addLayout(self.ui_verticalLayout_varList, 0, 0, 1, 1)
        self.ui_dockWidget_var_Content.setLayout(self.ui_gridLayout_dock_var)
        self.ui_dockWideget_var.setWidget(self.ui_dockWidget_var_Content)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.ui_dockWideget_var)
        
        #
        self.ui_horizontalLayout = QtWidgets.QHBoxLayout()
        #self.ui_horizontalLayout.addLayout(self.ui_verticalLayout_varList)
        
        self.ui_gridlayout = QtWidgets.QGridLayout()
        self.ui_gridlayout.addLayout(self.ui_horizontalLayout, 0, 0, 1, 1)
        
        self.ui_centralWidget = QtWidgets.QWidget()
        self.ui_centralWidget.setLayout(self.ui_gridlayout)
        self.setCentralWidget(self.ui_centralWidget)
        
    def initNonUiMembers(self, wtype, index):
        self.w_index=index
        self.w_name = wtype + str(self.w_index)
        
        self.uds_variable_name_prefix_list = []
        self.uds_variable_name_list = []        
        self.uds_variable_pt_list = []        
        
        self.uds_variable_history_list = []        
    
    """ @SLOTS of UI Widgets"""
    #
    def varNameListRowChanged(self):
        self.updateHistoryList()

    ### GUIVarManger Interaction ###
    def sendDataSingalEmit(self):
        var_index = self.ui_lw_uds_variable_name_list.currentRow()
        self.sendDataSignal.emit(self.w_name, var_index)
        
    """ Regular Functions """
    def appendToLocalVarList(self, uds_data):
        data_name = uds_data.name
        if data_name in self.uds_variable_name_list:
            count = 1
            while True:
                count += 1
                if not data_name + str(count) in self.uds_variable_name_list:
                    uds_data.name = data_name + str(count)
                    break        

        self.uds_variable_name_prefix_list.append('  ')
        self.uds_variable_name_list.append(uds_data.name)
        self.uds_variable_pt_list.append(uds_data)
        
        self.updateVarList()
        
    def removeFromLocalVarList(self):
        ct_var_index = self.ui_lw_uds_variable_name_list.currentRow()
        if ct_var_index >= 0:
            self.uds_variable_name_prefix_list.pop(ct_var_index)
            self.uds_variable_name_list.pop(ct_var_index)
            self.uds_variable_pt_list.pop(ct_var_index)
        
            self.updateVarList()
            
            if ct_var_index > len(self.uds_variable_name_list)-1:
                self.ui_lw_uds_variable_name_list.setCurrentRow(len(self.uds_variable_name_list)-1)
            else:
                self.ui_lw_uds_variable_name_list.setCurrentRow(ct_var_index)
        
    def updateVarList(self):
        self.ui_lw_uds_variable_name_list.clear()
        
        for i in range(len(self.uds_variable_name_list)):
            self.ui_lw_uds_variable_name_list.addItem(self.uds_variable_name_prefix_list[i] 
                                                      + '-' 
                                                      + self.uds_variable_name_list[i])
        
    def updateHistoryList(self):
        self.ui_lw_uds_variable_history_list.clear()
        ct_var_index = self.ui_lw_uds_variable_name_list.currentRow()
        if ct_var_index >= 0:
            self.ui_lw_uds_variable_history_list.addItems(self.uds_variable_pt_list[ct_var_index].proc_history)

    

        

        

        
        