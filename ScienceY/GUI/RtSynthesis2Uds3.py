# -*- coding: utf-8 -*-
"""
Created on Mon Oct  2 11:48:05 2023

@author: jiaha
"""


"""
System modules
"""

"""
Third-party Modules
"""
import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui

"""
User Modules
"""

from .GuiFrame import GuiFrame
from .Image2Uds3Widget import Image2Uds3Widget

from ..RawDataProcess.UdsDataProcess import UdsDataStru
from ..ImageSimulate.GenerateCurve2D import sinusoidal2D
from .ConfigManager import ConfigManager
from .customizedWidgets.SimplifiedNumberLineEditor import SimplifiedNumberLineEditor
"""
Function Modules
"""

class RtSynthesis2Uds3(GuiFrame):
    def __init__(self, wtype, index, *args, **kwargs):
        super(RtSynthesis2Uds3, self).__init__(wtype, index, *args, **kwargs)        
        
        self.initCcNonUiMembers()
        self.initCcUiMembers()
        self.initCcUiLayout()        
             
        self.initCcMenuBar()

        #
        self.initPreference()
        
    """ Initializations"""
    def initPreference(self):
        self.ui_img_widget_main.setSettings(self.settings)
            
    def initCcUiMembers(self):        
        self.ui_img_widget_main = Image2Uds3Widget()
        self.ui_img_widget_main.ui_lb_widget_name.setText("<b>--- Synthesis ---</b>")
        #self.ui_img_widget_main.sendMsgSignal.connect(self.getMsgFromImgMainWidget)
        
        #
        self.ui_lb_function_title = QtWidgets.QLabel("<b>--- Function ---</b>")
        self.ui_lb_function_title.setMaximumHeight(50)
        self.ui_lb_function_equation = QtWidgets.QLabel("Sum[A_j * cos(<b>Q</b>_j * <b>r</b> - PHI_j)]")
        self.ui_lb_function_equation.setMaximumHeight(50)
        
        self.ui_pb_add_wavevector = QtWidgets.QPushButton("Add Q_j")
        self.ui_pb_add_wavevector.clicked.connect(self.act_pb_add_wave_vector)
        self.ui_pb_remove_wavevector = QtWidgets.QPushButton("Remove Q_j")
        self.ui_pb_remove_wavevector.clicked.connect(self.act_pb_remove_wave_vector)
        self.ui_pb_save_var_to_list = QtWidgets.QPushButton("Save to Local Var")
        self.ui_pb_save_var_to_list.clicked.connect(self.act_pb_save_var_to_local_list)
        
        self.ui_sp_dSize_button = QtWidgets.QSpacerItem(200, 20)
        
        self.ui_lb_data_size = QtWidgets.QLabel("Data Size:")
        self.ui_le_data_size = QtWidgets.QLineEdit()
        self.ui_le_data_size.editingFinished.connect(self.act_data_size_changed)
        self.ui_le_data_size.setText('256')
        
        #
        self.ui_sa_wave_vectors = QtWidgets.QScrollArea()
        self.ui_sa_wave_vectors.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.ui_sa_wave_vectors.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.ui_sa_wave_vectors.setWidgetResizable(True)
        
        self.ui_qw_wavev_scroll_content = QtWidgets.QWidget()
        
    def initCcUiLayout(self):     
        #
        self.ui_cc_verticalLayout = QtWidgets.QVBoxLayout()
        self.ui_cc_verticalLayout.addWidget(self.ui_lb_function_title)
        self.ui_cc_verticalLayout.addWidget(self.ui_lb_function_equation)
        
        #
        self.ui_horizontalLayout_buttons = QtWidgets.QHBoxLayout()
        self.ui_horizontalLayout_buttons.addWidget(self.ui_lb_data_size)
        self.ui_horizontalLayout_buttons.addWidget(self.ui_le_data_size)
        self.ui_horizontalLayout_buttons.addItem(self.ui_sp_dSize_button)
        self.ui_horizontalLayout_buttons.addWidget(self.ui_pb_add_wavevector)
        self.ui_horizontalLayout_buttons.addWidget(self.ui_pb_remove_wavevector)
        self.ui_horizontalLayout_buttons.addWidget(self.ui_pb_save_var_to_list)
        
        #
        self.ui_cc_verticalLayout.addLayout(self.ui_horizontalLayout_buttons)
        
        #        
        self.ui_verticalLayout_wave_vectors = QtWidgets.QVBoxLayout()
        self.ui_verticalLayout_wave_vectors.setContentsMargins(0,0,0,0) # left, top, right, bottom
        self.ui_sa_wave_vectors.setWidget(self.ui_qw_wavev_scroll_content)
        self.ui_qw_wavev_scroll_content.setLayout(self.ui_verticalLayout_wave_vectors)
        self.ui_cc_verticalLayout.addWidget(self.ui_sa_wave_vectors)
                
        #
        self.ui_horizontalLayout.addWidget(self.ui_img_widget_main)
        self.ui_horizontalLayout.addLayout(self.ui_cc_verticalLayout)
        
    def initCcNonUiMembers(self):
        # Settings
        self.settings = self.loadSettings()
        
        #
        self.wave_vector_list = []
        self.data_size = 256
        self.data_simulated_sum = np.zeros((1, self.data_size, self.data_size))
        self.data_simulated_list = []
        
        self.uds_data = UdsDataStru(self.data_simulated_sum, 'uds3D_RtSynthesis')
        
        
    def initCcMenuBar(self):
        # Actions
        self.creat_actions()
        
        # connect actions
        self.connect_actions()
        
        # MenuBar
        self.creat_menuBar()
        
        # ToolBar
        #self._creat_toolBar()
        
        # StatusBar
        self.creat_statusBar()
        
    """ @SLOTS of UI Widgets"""
    
    def resizeEvent(self, event):                      
        screens = QtWidgets.QApplication.screens()                
        for s in screens:
            if s == QtWidgets.QApplication.screenAt(self.pos()):                
                width = int(0.33 * (s.size().width() + s.size().height())/2)
                height = width                
                self.ui_img_widget_main.setCanvasWidgetSize(width, height)
                
    def update_wave_vectors_layout(self, TYPE):
        if TYPE == 'ADD':
            idx = len(self.wave_vector_list) - 1
            self.ui_verticalLayout_wave_vectors.addWidget(self.wave_vector_list[idx])
        elif TYPE == 'REMOVE':
            idx = len(self.wave_vector_list) - 1
            self.ui_verticalLayout_wave_vectors.removeWidget(self.wave_vector_list[idx])
        else:
            print("Wrong type!")
        
    
    def act_pb_add_wave_vector(self):
        idx = len(self.wave_vector_list)
        if idx < 16:
            wv = WaveVectorParams(idx)
            wv.ParamsUpdateSignal.connect(self.act_wavevectors_params_updated)
        
            self.wave_vector_list.append(wv)
        
            self.update_wave_vectors_layout('ADD')
        
    def act_pb_remove_wave_vector(self):  
        idx = len(self.wave_vector_list)
        if idx > 1:        
            self.update_wave_vectors_layout('REMOVE')
            
            idx = len(self.wave_vector_list) - 1
            self.wave_vector_list.pop(idx)
            
            self.act_wavevectors_params_removed(idx)
    
    def act_wavevectors_params_removed(self, index):
        self.uds_data.data[0,:,:] = self.uds_data.data[0,:,:] - self.data_simulated_list[index]
        self.data_simulated_list.pop(index)
        
        self.ui_img_widget_main.setUdsData(self.uds_data)        
        
    def act_wavevectors_params_updated(self, index):
        qx = self.wave_vector_list[index].qx
        qy = self.wave_vector_list[index].qy
        amplitude = self.wave_vector_list[index].amplitude
        phase = self.wave_vector_list[index].phase   
        
        if len(self.data_simulated_list) < index + 1:
            self.data_simulated_list.append(sinusoidal2D(self.data_size, qx, qy, phase, amplitude))
            self.uds_data.data[0,:,:] = self.uds_data.data[0,:,:] + self.data_simulated_list[index]
        else:
            self.uds_data.data[0,:,:] = self.uds_data.data[0,:,:] - self.data_simulated_list[index]
            self.data_simulated_list[index] = sinusoidal2D(self.data_size, qx, qy, phase, amplitude)
            self.uds_data.data[0,:,:] = self.uds_data.data[0,:,:] + self.data_simulated_list[index]
            
        self.ui_img_widget_main.setUdsData(self.uds_data)
        
    def act_data_size_changed(self):
        if self.ui_le_data_size.text().isdecimal():
            self.data_size = int(self.ui_le_data_size.text())
        else:
            return
        
        self.data_simulated_list.clear()
        self.uds_data.data = np.zeros((1,self.data_size,self.data_size))
        
        
        for i in range(len(self.wave_vector_list)):
            qx = self.wave_vector_list[i].qx
            qy = self.wave_vector_list[i].qy
            amplitude = self.wave_vector_list[i].amplitude
            phase = self.wave_vector_list[i].phase
            
            print(qx,",", qy,",", amplitude,",", phase)
                        
            self.data_simulated_list.append(sinusoidal2D(self.data_size, qx, qy, phase, amplitude))
            self.uds_data.data[0,:,:] = self.uds_data.data[0,:,:] + self.data_simulated_list[i]
            
        
        
        self.ui_img_widget_main.setUdsData(self.uds_data)   
        
    def act_pb_save_var_to_local_list(self):
        uds3D_data_current_simulation = UdsDataStru(self.uds_data.data , 'uds3D_RtSynthesis' )
        uds3D_data_current_simulation.info['LayerValue']='0'
        
        self.appendToLocalVarList(uds3D_data_current_simulation)
        
    """ Regular Functions"""
    
    """ Settings """
    def loadSettings(self):
        return ConfigManager.load_settings_from_file('./ScienceY/config/RtSynthesis2Uds3.txt')
    
    def saveSettings(self):
        ConfigManager.save_settings_to_file('./ScienceY/config/RtSynthesis2Uds3.txt', self.settings)
  
    
        
    """    Menu and Actions    """       
    def creat_menuBar(self):
        menuBar = QtWidgets.QMenuBar(self)
        
        # Top Menu
        widgetssMenu = menuBar.addMenu("&Widgets")
        
        # Widgets Menu
        widgetssMenu.addAction(self.showVarDockWidget)
        
        #
        self.setMenuBar(menuBar)
    
    def creat_statusBar(self):
        self.status_bar = self.statusBar()
        
    def creat_actions(self):
        
        # Widgets Menu
        self.showVarDockWidget = QtWidgets.QAction("Varibals DockWidget",self)
        
    def connect_actions(self):
        #window
        self.showVarDockWidget.triggered.connect(self.actShowVarDockWidget)
    
    """   Slots for Menu Actions   """  
    
    # Widgets Menus
    def actShowVarDockWidget(self):
        self.ui_dockWideget_var.show()
        
        
        
""""""""""""""""""  

""""""""""""""""""


class WaveVectorParams(QtWidgets.QWidget):
    ParamsUpdateSignal = QtCore.pyqtSignal(int)
    def __init__(self, index, *args, **kwargs):
        super(WaveVectorParams, self).__init__(*args, **kwargs)
        
        self.initNonUiMembers(index) 
        self.initUiMembers()
        self.initUiLayout()       

        self.act_update_amplitude()
        self.act_updata_phase()               
        
    def initUiMembers(self):
        self.ui_lb_qx = QtWidgets.QLabel("qx")
        self.ui_lb_qx.setMaximumHeight(30)
        self.ui_le_qx = SimplifiedNumberLineEditor()
        self.ui_le_qx.setMaximumWidth(50)
        self.ui_le_qx.setText('0')
        self.ui_le_qx.validTextChanged.connect(self.act_qx_textChanged)
        
        self.ui_lb_qy = QtWidgets.QLabel("qy")
        self.ui_lb_qy.setMaximumHeight(30)
        self.ui_le_qy = SimplifiedNumberLineEditor()
        self.ui_le_qy.setMaximumWidth(50)
        self.ui_le_qy.setText('0')
        self.ui_le_qy.validTextChanged.connect(self.act_qy_textChanged)
        
        self.ui_lb_amplitude = QtWidgets.QLabel("Amplitude")
        self.ui_lb_amplitude.setMaximumHeight(30)
        self.ui_hs_amplitude = QtWidgets.QSlider()
        self.ui_hs_amplitude.setOrientation(QtCore.Qt.Horizontal)
        self.ui_hs_amplitude.setRange(0,100)     
        self.ui_hs_amplitude.setSingleStep(1)
        self.ui_hs_amplitude.setValue(0)
        self.ui_hs_amplitude.sliderMoved.connect(self.act_amplitude_slider_moved)
        self.ui_le_amplitude_min = QtWidgets.QLineEdit('0')
        self.ui_le_amplitude_min.editingFinished.connect(self.act_amplitude_min_textChanged)
        self.ui_le_amplitude_min.setMaximumWidth(60)
        self.ui_le_amplitude_max = QtWidgets.QLineEdit('1')
        self.ui_le_amplitude_max.editingFinished.connect(self.act_amplitude_max_textChanged)
        self.ui_le_amplitude_max.setMaximumWidth(60)
        self.ui_le_amplitude = QtWidgets.QLineEdit()
        self.ui_le_amplitude.setEnabled(False)
        
        self.ui_lb_phase = QtWidgets.QLabel("Phase")
        self.ui_lb_phase.setMaximumHeight(30)
        self.ui_hs_phase = QtWidgets.QSlider()
        self.ui_hs_phase.setOrientation(QtCore.Qt.Horizontal)
        self.ui_hs_phase.setRange(0,100)     
        self.ui_hs_phase.setSingleStep(1)
        self.ui_hs_phase.setValue(0)
        self.ui_hs_phase.sliderMoved.connect(self.act_phase_slider_moved)
        self.ui_le_phase_min = QtWidgets.QLineEdit('-3.14')
        self.ui_le_phase_min.editingFinished.connect(self.act_phase_min_textChanged)
        self.ui_le_phase_min.setMaximumWidth(80)
        self.ui_le_phase_max = QtWidgets.QLineEdit('3.14')
        self.ui_le_phase_max.editingFinished.connect(self.act_phase_max_textChanged)
        self.ui_le_phase_max.setMaximumWidth(80)
        self.ui_le_phase = QtWidgets.QLineEdit()
        self.ui_le_phase.setEnabled(False)
        
    def initUiLayout(self):
        self.ui_verticalLayout_qx = QtWidgets.QVBoxLayout()
        if self.index == 0:
            self.ui_verticalLayout_qx.addWidget(self.ui_lb_qx)
        self.ui_verticalLayout_qx.addWidget(self.ui_le_qx)
        
        self.ui_verticalLayout_qy = QtWidgets.QVBoxLayout()
        if self.index == 0:
            self.ui_verticalLayout_qy.addWidget(self.ui_lb_qy)
        self.ui_verticalLayout_qy.addWidget(self.ui_le_qy)
        
        self.ui_horizontalLayout_amp = QtWidgets.QHBoxLayout()
        self.ui_horizontalLayout_amp.addWidget(self.ui_le_amplitude_min)
        self.ui_horizontalLayout_amp.addWidget(self.ui_hs_amplitude)
        self.ui_horizontalLayout_amp.addWidget(self.ui_le_amplitude_max)
        self.ui_verticalLayout_amp = QtWidgets.QVBoxLayout()
        if self.index == 0:
            self.ui_verticalLayout_amp.addWidget(self.ui_lb_amplitude)
        self.ui_verticalLayout_amp.addLayout(self.ui_horizontalLayout_amp)
        self.ui_verticalLayout_amp.addWidget(self.ui_le_amplitude)
        
        self.ui_horizontalLayout_phase = QtWidgets.QHBoxLayout()
        self.ui_horizontalLayout_phase.addWidget(self.ui_le_phase_min)
        self.ui_horizontalLayout_phase.addWidget(self.ui_hs_phase)
        self.ui_horizontalLayout_phase.addWidget(self.ui_le_phase_max)
        self.ui_verticalLayout_phase = QtWidgets.QVBoxLayout()
        if self.index == 0:
            self.ui_verticalLayout_phase.addWidget(self.ui_lb_phase)
        self.ui_verticalLayout_phase.addLayout(self.ui_horizontalLayout_phase)
        self.ui_verticalLayout_phase.addWidget(self.ui_le_phase)
        
        self.ui_horizontalLayout = QtWidgets.QHBoxLayout()
        self.ui_horizontalLayout.addLayout(self.ui_verticalLayout_qx)
        self.ui_horizontalLayout.addLayout(self.ui_verticalLayout_qy)
        self.ui_horizontalLayout.addLayout(self.ui_verticalLayout_amp)
        self.ui_horizontalLayout.addLayout(self.ui_verticalLayout_phase)
        
        self.ui_gridlayout = QtWidgets.QGridLayout()
        self.ui_gridlayout.addLayout(self.ui_horizontalLayout, 0, 0, 1, 1)        
        self.setLayout(self.ui_gridlayout)
        
    def initNonUiMembers(self, index):
        self.index = index
        self.qx = 0
        self.qy = 0
        self.amplitude = 0
        self.phase = 0
        
    """ SIGNALS """
    def sendParamsUpdateSignal(self):
        self.ParamsUpdateSignal.emit(self.index)
        
    """ SLOTs"""    
    
    def act_qx_textChanged(self):
        self.qx = self.ui_le_qx.value()    
        
        self.sendParamsUpdateSignal()
    
    def act_qy_textChanged(self):
        self.qy = self.ui_le_qy.value()
        
        self.sendParamsUpdateSignal()
    
    def act_update_amplitude(self):
        amp_min = float(self.ui_le_amplitude_min.text())
        amp_max = float(self.ui_le_amplitude_max.text())
        
        percent = float(self.ui_hs_amplitude.value()) /100
        amp = int(((amp_max -  amp_min) * percent + amp_min ) * 1e6) / 1e6
        self.ui_le_amplitude.setText(str(amp))
        
        self.amplitude = amp
        
        self.sendParamsUpdateSignal()
        
    def act_updata_phase(self):
        phase_min = float(self.ui_le_phase_min.text())
        phase_max = float(self.ui_le_phase_max.text())
        
        percent = float(self.ui_hs_phase.value()) /100
        phase = int(((phase_max -  phase_min) * percent + phase_min ) * 1e6) / 1e6
        self.ui_le_phase.setText(str(phase))
        
        self.phase = phase
        
        self.sendParamsUpdateSignal()
    
    def act_amplitude_min_textChanged(self):
        self.act_update_amplitude()
    def act_amplitude_max_textChanged(self):
        self.act_update_amplitude()

    def act_amplitude_slider_moved(self):
        self.act_update_amplitude()
        
    def act_phase_min_textChanged(self):
        self.act_updata_phase()
    def act_phase_max_textChanged(self):   
        self.act_updata_phase()
    def act_phase_slider_moved(self):
        self.act_updata_phase()