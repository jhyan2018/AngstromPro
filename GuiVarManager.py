# -*- coding: utf-8 -*-
"""
Created on Thu Jul 27 09:56:53 2023

@author: Huiyu's Jiahao Yan
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
from ScienceY.GUI import ImageUdsData2or3D, RtSynthesis2D
from ScienceY.RawDataProcess import NanonisDataProcess, TxtDataProcess, LFDataProcess
from ScienceY.RawDataProcess.UdsDataStru import UdsDataStru3D
"""
Modules Definition
"""

""" *************************************** """
""" DO NOT MODIFY THE REGION UNTIL INDICATED"""
""" *************************************** """
    
class GuiVarManager(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(GuiVarManager, self).__init__(*args, **kwargs)
        
        self.initUiMembers()
        self.initUiLayout()        
        self.initNonUiMembers()        

        self.initMenuBar()
        self.initChildWindows()
        
    """ Initializations"""
    def initUiMembers(self):
        
        self.setWindowTitle("GUI & Var Manager")
        self.resize(600,300)
        
        #variables
        self.ui_lw_uds_variable_name_list = QtWidgets.QListWidget()

        #child widgets
        self.ui_lw_uds_window_list = QtWidgets.QListWidget()
        
        #other widgets       
        self.ui_lb_varibale = QtWidgets.QLabel("USD Variables")
        self.ui_lb_window = QtWidgets.QLabel("Alive Windows")

        self.ui_pb_update_var_list =  QtWidgets.QPushButton("Update")
        self.ui_pb_update_var_list.clicked.connect(self.updateVarList) 
        
        self.ui_pb_send_var_to_window =  QtWidgets.QPushButton("-> Send -> ")
        self.ui_pb_send_var_to_window.clicked.connect(self.sendDataToWindow) 
        
        self.ui_pb_remove_window =  QtWidgets.QPushButton("Remove")
        self.ui_pb_remove_window.clicked.connect(self.removeWindow) 
                
        self.ui_pb_show_window =  QtWidgets.QPushButton("Show")
        self.ui_pb_show_window.clicked.connect(self.showSelectedWindow)
        
        self.ui_sb_wd_pb_spacer = QtWidgets.QSpacerItem(20, 120)
        
    def initUiLayout(self):
        self.ui_verticalLayout1 = QtWidgets.QVBoxLayout()
        self.ui_verticalLayout1.addWidget(self.ui_pb_update_var_list)
        
        self.ui_verticalLayout2 = QtWidgets.QVBoxLayout()
        self.ui_verticalLayout2.addWidget(self.ui_lb_varibale)
        self.ui_verticalLayout2.addWidget(self.ui_lw_uds_variable_name_list)
        
        self.ui_verticalLayout3 = QtWidgets.QVBoxLayout()
        self.ui_verticalLayout3.addWidget(self.ui_pb_send_var_to_window)
        
        
        self.ui_verticalLayout4 = QtWidgets.QVBoxLayout()
        self.ui_verticalLayout4.addWidget(self.ui_lb_window)
        self.ui_verticalLayout4.addWidget(self.ui_lw_uds_window_list)
        
        self.ui_verticalLayout5 = QtWidgets.QVBoxLayout()        
        self.ui_verticalLayout5.addWidget(self.ui_pb_show_window)
        self.ui_verticalLayout5.addItem(self.ui_sb_wd_pb_spacer)
        self.ui_verticalLayout5.addWidget(self.ui_pb_remove_window)
        
        self.ui_horizontalLayout = QtWidgets.QHBoxLayout()
        self.ui_horizontalLayout.addLayout(self.ui_verticalLayout1)
        self.ui_horizontalLayout.addLayout(self.ui_verticalLayout2)
        self.ui_horizontalLayout.addLayout(self.ui_verticalLayout3) 
        self.ui_horizontalLayout.addLayout(self.ui_verticalLayout4)
        self.ui_horizontalLayout.addLayout(self.ui_verticalLayout5)
                        
        self.ui_gridlayout = QtWidgets.QGridLayout()
        self.ui_gridlayout.addLayout(self.ui_horizontalLayout, 0, 0, 1, 1)
        
        self.ui_centralWidget = QtWidgets.QWidget()
        self.ui_centralWidget.setLayout(self.ui_gridlayout)
        self.setCentralWidget(self.ui_centralWidget)    

    def initNonUiMembers(self):
        self.uds_variable_name_list =[]
                
        self.alive_window_pt_list = []
        self.alive_window_name_list = []
        self.created_window_counts = 0
        
        self.updateVarList()
        
        # timer
        self.timer1 = QtCore.QTimer()
        self.timer1.timeout.connect(self.updateWigetsStatus)
        self.timer1.setInterval(400)
        self.timer1.start()
        
    def initMenuBar(self):
        # Actions
        self.creatActions()
        
        # connect actions
        self.connectActions()
        
        # MenuBar
        self.creatMenuBar()
        
        # ToolBar
        #self._creat_toolBar()

    """ @SLOTS of UI Widgets"""
    
    # timer
    def updateWigetsStatus(self):
        var_list_cnt = self.ui_lw_uds_variable_name_list.count()
        win_list_cnt = self.ui_lw_uds_window_list.count()
        if  var_list_cnt < 1 or win_list_cnt < 1:
            self.ui_pb_send_var_to_window.setEnabled(False)
        else:
            self.ui_pb_send_var_to_window.setEnabled(True)
            
        if win_list_cnt < 1:
            self.ui_pb_remove_window.setEnabled(False)
            self.ui_pb_show_window.setEnabled(False)
        else:
            self.ui_pb_remove_window.setEnabled(True)
            self.ui_pb_show_window.setEnabled(True)            
        
    # button
    def updateVarList(self):
        self.uds_variable_name_list=[]
        var_del_list = []
        for i in globals().keys():
            if 'uds' in i:
                if globals()[i].name == i:
                    self.uds_variable_name_list.append(i)
                else:
                    self.uds_variable_name_list.append(globals()[i].name)
                    var_del_list.append(i)
                    
        for i in var_del_list: # make sure var name is consistent with uds_data.name
            globals()[globals()[i].name] = globals()[i] 
            del globals()[i]                    
                
        self.ui_lw_uds_variable_name_list.clear()
        self.ui_lw_uds_variable_name_list.addItems(self.uds_variable_name_list)
        
        ct_var_index = self.ui_lw_uds_variable_name_list.currentRow()
        if ct_var_index == -1:
            self.ui_lw_uds_variable_name_list.setCurrentRow(0)
            
    def removeWindow(self):
        ct_w_index = self.ui_lw_uds_window_list.currentRow()
        
        if ct_w_index >= 0:
            self.alive_window_pt_list[ct_w_index].deleteLater()
            self.alive_window_pt_list.pop(ct_w_index)
            self.alive_window_name_list.pop(ct_w_index)
            
            self.updateAlivedWindowList()        
        
    def showSelectedWindow(self):
        ct_w_index = self.ui_lw_uds_window_list.currentRow()
        self.alive_window_pt_list[ct_w_index].show()
        
    def updateAlivedWindowList(self):
        self.ui_lw_uds_window_list.clear()
        self.ui_lw_uds_window_list.addItems(self.alive_window_name_list)
        
        ct_w_index = self.ui_lw_uds_window_list.currentRow()
        if ct_w_index == -1:
            self.ui_lw_uds_window_list.setCurrentRow(0)
        
    def sendDataToWindow(self):
        ct_var_index = self.ui_lw_uds_variable_name_list.currentRow()
        ct_w_index = self.ui_lw_uds_window_list.currentRow()
                
        dataName = self.uds_variable_name_list[ct_var_index]
        dataCopy = UdsDataStru3D(globals()[dataName].data, globals()[dataName].name)        
        dataCopy.proc_history = globals()[dataName].proc_history
        dataCopy.info = globals()[dataName].info
        
        self.alive_window_pt_list[ct_w_index].appendToLocalVarList(dataCopy)
    
        
    # from child windows
    @QtCore.pyqtSlot(str, int)
    def getDataFromWindows(self, w_name, var_index):
        w_index = self.alive_window_name_list.index(w_name)
        var_name = self.alive_window_pt_list[w_index].uds_variable_name_list[var_index]
        globals()[var_name] = UdsDataStru3D(self.alive_window_pt_list[w_index].uds_variable_pt_list[var_index].data ,var_name)
        globals()[var_name].proc_history = self.alive_window_pt_list[w_index].uds_variable_pt_list[var_index].proc_history
        globals()[var_name].info = self.alive_window_pt_list[w_index].uds_variable_pt_list[var_index].info        
        
        
    """ Regular Functions """
    


        
        
    """ *************************************************************** """
    """ INDICATION: MODIFY THE FOLLOWING CODE UNTIL INDICATED IF NEEDED """
    """ *************************************************************** """
    
    """    Menu and Actions    """
    def creatMenuBar(self):
        menuBar = QtWidgets.QMenuBar(self)
        
        ### 1st Level Menu ###
        
        fileMenu = menuBar.addMenu("&File")
        editMenu = menuBar.addMenu("&Edit")
        windowMenu = menuBar.addMenu("&Window")

        #### 2nd Level Menu###
        
        # File Menu
        fileMenu.addAction(self.loadFromFileAction)
        fileMenu.addAction(self.saveToFileAction)
        
        # Edit Menu
        #findMenu = editMenu.addMenu("&Find and Replace")
        #findMenu.addAction(self.findAction)
        
        # Window Menu
        windowMenu.addAction(self.image2or3DAction)
        windowMenu.addAction(self.rtSynthesis2DAction)
        
        ### ###
        self.setMenuBar(menuBar)
        
    #def _creat_toolBar(self):
        #fileToolBar = self.addToolBar("File")
        
        #fileToolBar.addAction(self.openAction)
        
    def creatActions(self):
        # File Menu
        self.loadFromFileAction = QtWidgets.QAction("&LoadFromFile",self)
        self.saveToFileAction = QtWidgets.QAction("&SaveToFile",self)
        
        self.findAction = QtWidgets.QAction("&Find",self)
        self.replaceAction = QtWidgets.QAction("&Replace",self)
        
        # Window
        self.image2or3DAction = QtWidgets.QAction("Image2or3D",self)
        self.rtSynthesis2DAction = QtWidgets.QAction("RtSynthesis2D",self)
        
    def connectActions(self):
        # File Menu
        self.loadFromFileAction.triggered.connect(self.loadFromFile)
        self.saveToFileAction.triggered.connect(self.saveToFile)
        
        # Window Menu
        self.image2or3DAction.triggered.connect(self.newImage2or3DWindow)
        self.rtSynthesis2DAction.triggered.connect(self.newRtSynthesis2D)
        
    """   Slots for Menu Actions   """     
    #
    def loadFromFile(self):
        print("Load From File")
        data_path = 'E:/gdrive/Python/STM_Data/'
        data_type ='Data Files (*.3ds *.sxm *.dat *.tfr *.1fl *.2fl *.ffl *.1fr *.txt)'

        file = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", data_path, data_type)
        full_path = file[0]
        file_name = full_path.split('/')[-1].split('.')[0]
        file_type = full_path.split('/')[-1].split('.')[-1]
        
        if file_type == '3ds':
            globals()['data3ds'] = NanonisDataProcess.Data3dsStru(full_path)  
            #data3ds = NanonisDataProcess.Data3dsStru(full_path)            
            globals()['uds3D_'+file_name+'_topo'] = data3ds.get_Topo()
            globals()['uds3D_'+file_name+'_dIdV'] = data3ds.get_dIdV_data()
        elif file_type == 'sxm':
            globals()['dataSxm'] = NanonisDataProcess.DataSxmStru(full_path)
            #dataSxm = NanonisDataProcess.DataSxmStru(full_path)
            globals()['uds3D_'+file_name+'_topo_fwd'] = dataSxm.get_Topo_fwd()
            globals()['uds3D_'+file_name+'_topo_bwd'] = dataSxm.get_Topo_bwd()
            globals()['uds3D_'+file_name+'_dIdV_fwd'] = dataSxm.get_dIdV_fwd()
            globals()['uds3D_'+file_name+'_dIdV_bwd'] = dataSxm.get_dIdV_bwd()
            globals()['uds3D_'+file_name+'_Currrent_fwd'] = dataSxm.get_Current_fwd()
            globals()['uds3D_'+file_name+'_Current_bwd'] = dataSxm.get_Current_bwd()
        elif file_type == 'TFR':
            data1fl = LFDataProcess.Data1FLStru(full_path)
            globals()['uds3D_'+file_name+'_topo'] = data1fl.get_data()       
        elif file_type == '1FL':
            data1fl = LFDataProcess.Data1FLStru(full_path)
            globals()['uds3D_'+file_name+'_dIdV'] = data1fl.get_data()
        elif file_type == 'txt':
            dataTxt = TxtDataProcess.DataTxtStru(full_path)   
            globals()['uds3D_'+file_name] = dataTxt.get_txt_data()
        else:
            pass
        
    def saveToFile(self):
        
        print("Save to File")
        

    
    # creat new window
    def newImage2or3DWindow(self):
        self.created_window_counts += 1
        
        w = ImageUdsData2or3D('Image 2or3D_', self.created_window_counts)
        w.sendDataSignal.connect(self.getDataFromWindows)
        
        self.alive_window_pt_list.append(w)        
        self.alive_window_name_list.append('Image 2or3D_'+str(self.created_window_counts))
        
        self.updateAlivedWindowList()
        
    def newRtSynthesis2D(self):
        self.created_window_counts += 1
        
        w = RtSynthesis2D('RtSynthesis 2D_', self.created_window_counts)
        w.sendDataSignal.connect(self.getDataFromWindows)
        
        self.alive_window_pt_list.append(w)        
        self.alive_window_name_list.append('RtSynthesis 2D_'+str(self.created_window_counts))
        
        self.updateAlivedWindowList()
    
    def initChildWindows(self):
        self.newImage2or3DWindow()
    


        


""" *************************************** """
""" DO NOT MODIFY THE FOLLOWING REGION"""
""" *************************************** """        

if __name__ == "__main__":   

    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)
    w = GuiVarManager()    
    w.show()