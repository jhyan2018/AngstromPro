# -*- coding: utf-8 -*-
"""
Created on Thu Jul 27 09:56:53 2023

@author: Jiahao Yan & Huiyu Zhao
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
from ScienceY.GUI import Image2Uds3, Plot1Uds2, RtSynthesis2Uds3, DataBrowser
from ScienceY.GUI.ConfigManager import ConfigManager
from ScienceY.RawDataProcess import NanonisDataProcess, TxtDataProcess, LFDataProcess
from ScienceY.RawDataProcess.UdsDataProcess import UdsDataProcess, UdsDataStru3D
"""
Modules Definition
"""

""" *************************************** """
""" DO NOT MODIFY THE REGION UNTIL INDICATED"""
""" *************************************** """
class GVMSettings(QtWidgets.QWidget):
    save_settings = QtCore.pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        super(GVMSettings, self).__init__(*args, **kwargs)
        
        self.initUiMembers()
        self.initUiLayout()
        
    def setSettings(self, settings):
        self.settings = settings       
        self.ui_le_data_path.setText(self.settings['PATH']['data_path'])
        
    def initUiMembers(self):
        self.ui_lb_data_path = QtWidgets.QLabel('Data path:')
        self.ui_le_data_path = QtWidgets.QLineEdit()
        self.ui_pb_change_data_path = QtWidgets.QPushButton('C')
        self.ui_pb_change_data_path.clicked.connect(self.browseDirectry)
        self.ui_pb_change_data_path.setMaximumSize(40,40)
        
        self.ui_pb_save_settings = QtWidgets.QPushButton('Save')
        self.ui_pb_save_settings.clicked.connect(self.saveSettings)
        
    def initUiLayout(self):
        ui_horizontalLayout1 = QtWidgets.QHBoxLayout()
        ui_horizontalLayout1.addWidget(self.ui_lb_data_path)
        ui_horizontalLayout1.addWidget(self.ui_le_data_path)
        ui_horizontalLayout1.addWidget(self.ui_pb_change_data_path)
        
        ui_verticalLayout1 = QtWidgets.QVBoxLayout()
        ui_verticalLayout1.addLayout(ui_horizontalLayout1)
        ui_verticalLayout1.addWidget(self.ui_pb_save_settings)
        
        ui_gridlayout = QtWidgets.QGridLayout()
        ui_gridlayout.addLayout(ui_verticalLayout1, 0, 0, 1, 1)
        #ui_gridlayout.setContentsMargins(0,0,0,0) # left, top, right, bottom
        
        self.setLayout(ui_gridlayout) 
        
    """ @SLOT"""    
    def saveSettings(self):
        self.save_settings.emit()
    
    def browseDirectry(self):
        data_type ='Data Files (*.uds *.3ds *.sxm *.dat *.tfr *.1fl *.2fl *.ffl *.1fr *.txt)'
        data_path = self.ui_le_data_path.text()
        
        file = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", data_path, data_type)
        if not file[0] == '':
            new_data_path = file[0][0:-len(file[0].split('/')[-1])]
            self.ui_le_data_path.setText(new_data_path)
            self.settings['PATH']['data_path'] = new_data_path
    
class GuiVarManager(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(GuiVarManager, self).__init__(*args, **kwargs)
        
        self.initUiMembers()
        self.initUiLayout()        
        self.initNonUiMembers()      
        
        #
        self.ui_dockWidget_settings_content.setSettings(self.settings)
        
        #
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
        
        # dockWiget Pereference
        self.ui_dockWidget_settings = QtWidgets.QDockWidget()
        self.ui_dockWidget_settings_content = GVMSettings()
        self.ui_dockWidget_settings_content.save_settings.connect(self.saveSettings)

        self.ui_dockWidget_settings.setWidget(self.ui_dockWidget_settings_content)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea , self.ui_dockWidget_settings)
        self.ui_dockWidget_settings.close()
        
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
        
        # Settings
        self.settings = self.loadSettings()
        
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
        dataCopy.info = globals()[dataName].info.copy()
        dataCopy.proc_history = globals()[dataName].proc_history.copy()
        dataCopy.proc_to_do = globals()[dataName].proc_to_do.copy()
        
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
    
    """ Settings """
    def loadSettings(self):
        return ConfigManager.load_settings_from_file('./ScienceY/config/GuiVarManager.txt')
    
    def saveSettings(self):
        ConfigManager.save_settings_to_file('./ScienceY/config/GuiVarManager.txt', self.settings)

        
        
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
        optionMenu = menuBar.addMenu("&Option")

        #### 2nd Level Menu###
        
        # File Menu
        fileMenu.addAction(self.loadFromFileAction)
        fileMenu.addAction(self.saveToFileAction)
        
        # Edit Menu
        #findMenu = editMenu.addMenu("&Find and Replace")
        #findMenu.addAction(self.findAction)
        
        # Window Menu
        windowMenu.addAction(self.dataBrowserAction)
        windowMenu.addAction(self.image2or3DAction)
        windowMenu.addAction(self.rtSynthesis2DAction)
        
        
        # Option Menu
        optionMenu.addAction(self.preferenceAction)
        
        ### ###
        self.setMenuBar(menuBar)
        
    #def _creat_toolBar(self):
        #fileToolBar = self.addToolBar("File")
        
        #fileToolBar.addAction(self.openAction)
        
    def creatActions(self):
        # File Menu
        self.loadFromFileAction = QtWidgets.QAction("&Load From File",self)
        self.saveToFileAction = QtWidgets.QAction("&Save To File",self)
        
        self.findAction = QtWidgets.QAction("&Find",self)
        self.replaceAction = QtWidgets.QAction("&Replace",self)
        
        # Window
        self.dataBrowserAction = QtWidgets.QAction("Data Browser",self)
        self.image2or3DAction = QtWidgets.QAction("Image2or3D",self)
        self.rtSynthesis2DAction = QtWidgets.QAction("RtSynthesis2D",self)
        
        # Option
        self.preferenceAction = QtWidgets.QAction("Preference",self)
        
    def connectActions(self):
        # File Menu
        self.loadFromFileAction.triggered.connect(self.loadFromFile)
        self.saveToFileAction.triggered.connect(self.saveToFile)
        
        # Window Menu
        self.dataBrowserAction.triggered.connect(self.newDataBrowserWindow)
        self.image2or3DAction.triggered.connect(self.newImage2or3DWindow)
        self.rtSynthesis2DAction.triggered.connect(self.newRtSynthesis2D)
        
        # Option Menu
        self.preferenceAction.triggered.connect(self.preference)
        
    """   Slots for Menu Actions   """     
    #
    def loadFromFile(self):
        data_path = self.settings['PATH']['data_path']
        data_type ='Data Files (*.uds *.3ds *.sxm *.dat *.tfr *.1fl *.2fl *.ffl *.1fr *.txt)'

        file = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", data_path, data_type)
        full_path = file[0]
        file_name = full_path.split('/')[-1].split('.')[0]
        file_type = full_path.split('/')[-1].split('.')[-1]
        if '+' in file_name:
            file_name = file_name.replace('+','p')
        if '-' in file_name:
            file_name = file_name.replace('-','n')

        
        if file_type == '3ds':
            globals()['data3ds'] = NanonisDataProcess.Data3dsStru(full_path, file_name)  
            globals()['uds3D_'+file_name+'_topo'] = data3ds.get_Topo()
            if ('LI Demod 1 X (A)' in data3ds.channel_list) or ('Input 2 (V)' in data3ds.channel_list): 
                globals()['uds3D_'+file_name+'_dIdV'] = data3ds.get_dIdV_data()
            if 'Current (A)' in data3ds.channel_list:
                globals()['uds3D_'+file_name+'_Current'] = data3ds.get_Current()
            if 'LI Demod 1 Y (A)' in data3ds.channel_list:
                globals()['uds3D_'+file_name+'_Phase'] = data3ds.get_Phase()
        elif file_type == 'sxm':
            globals()['dataSxm'] = NanonisDataProcess.DataSxmStru(full_path, file_name)
            if 'Z' in dataSxm.channel_list[0]:
                globals()['uds3D_'+file_name+'_topo_fwd'] = dataSxm.get_Topo_fwd()
                if dataSxm.channel_list[1][dataSxm.channel_list[0].index('Z')] == 'both':
                    globals()['uds3D_'+file_name+'_topo_bwd'] = dataSxm.get_Topo_bwd()
            if 'LI_Demod_1_X' in dataSxm.channel_list[0]:
                globals()['uds3D_'+file_name+'_dIdV_fwd'] = dataSxm.get_dIdV_fwd()
                if dataSxm.channel_list[1][dataSxm.channel_list[0].index('LI_Demod_1_X')] == 'both':
                    globals()['uds3D_'+file_name+'_dIdV_bwd'] = dataSxm.get_dIdV_bwd()
            if 'Current' in dataSxm.channel_list[0]:
                globals()['uds3D_'+file_name+'_Currrent_fwd'] = dataSxm.get_Current_fwd()
                if dataSxm.channel_list[1][dataSxm.channel_list[0].index('Current')] == 'both':
                    globals()['uds3D_'+file_name+'_Current_bwd'] = dataSxm.get_Current_bwd()
            if 'LI_Demod_1_Y' in dataSxm.channel_list[0]:
                globals()['uds3D_'+file_name+'_theta'] = dataSxm.get_theta()
        elif file_type == 'TFR':
            data1fl = LFDataProcess.Data1FLStru(full_path)
            globals()['uds3D_'+file_name+'_topo'] = data1fl.get_data()       
        elif file_type == '1FL':
            data1fl = LFDataProcess.Data1FLStru(full_path)
            globals()['uds3D_'+file_name+'_dIdV'] = data1fl.get_data()
        elif file_type == 'txt':
            dataTxt = TxtDataProcess.DataTxtStru(full_path)   
            globals()['uds3D_'+file_name] = dataTxt.get_txt_data()
        elif file_type == 'uds':
            udp = UdsDataProcess(full_path)
            uds_data = udp.readFromFile()
            globals()[uds_data.name] = uds_data
        else:
            pass
        
    def saveToFile(self):                        
        if self.ui_lw_uds_variable_name_list.count() < 1:
            print('No variables.')
            return -1
        else:
            print("Save to File")
        
        data_path = self.settings['PATH']['data_path']
        data_type ='Data Files (*.uds)'
        
        c_row = self.ui_lw_uds_variable_name_list.currentRow()
        data_name = self.uds_variable_name_list[c_row]
        f_data_name = data_name[6: len(data_name)]
        data_full_path = data_path + f_data_name
        
        file = QtWidgets.QFileDialog.getSaveFileName(self, "Save File", data_full_path, data_type)
        full_path = file[0]
        if full_path == '':
            return -1
        
        file_type = full_path.split('/')[-1].split('.')[-1]
        
        if file_type == 'uds':
            udp = UdsDataProcess(full_path)
            udp.saveToFile(globals()[data_name])
        else:
            print('Unknown file type.')

    
    # creat new window
    def newDataBrowserWindow(self):
        self.created_window_counts += 1
        
        w = DataBrowser('DataBrowser_', self.created_window_counts)
        w.sendDataSignal.connect(self.getDataFromWindows)
        
        self.alive_window_pt_list.append(w)        
        self.alive_window_name_list.append('DataBrowser_'+str(self.created_window_counts))
        
        self.updateAlivedWindowList()     
        
    def newImage2or3DWindow(self):
        self.created_window_counts += 1
        
        w = Image2Uds3('Image2U3_', self.created_window_counts)
        w.sendDataSignal.connect(self.getDataFromWindows)
        
        self.alive_window_pt_list.append(w)        
        self.alive_window_name_list.append('Image2U3_'+str(self.created_window_counts))
        
        self.updateAlivedWindowList()
        
    def newPlot1Uds2Window(self):
        self.created_window_counts += 1
        
        w = Plot1Uds2('Plot1U2_', self.created_window_counts)
        w.sendDataSignal.connect(self.getDataFromWindows)
        
        self.alive_window_pt_list.append(w)        
        self.alive_window_name_list.append('Plot1U2_'+str(self.created_window_counts))
        
        self.updateAlivedWindowList()
        
    def newRtSynthesis2D(self):
        self.created_window_counts += 1
        
        w = RtSynthesis2Uds3('RtSynthesis2U3_', self.created_window_counts)
        w.sendDataSignal.connect(self.getDataFromWindows)
        
        self.alive_window_pt_list.append(w)        
        self.alive_window_name_list.append('RtSynthesis2U3_'+str(self.created_window_counts))
        
        self.updateAlivedWindowList()
    
    def initChildWindows(self):
        self.newDataBrowserWindow()
        self.newImage2or3DWindow()
        self.newPlot1Uds2Window()
    
    # Options
    def preference(self):
        self.ui_dockWidget_settings.show()

    
        


""" *************************************** """
""" DO NOT MODIFY THE FOLLOWING REGION"""
""" *************************************** """        

if __name__ == "__main__":   

    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)
    w = GuiVarManager()    
    w.show()
    #sys.exit(qapp.exec_())