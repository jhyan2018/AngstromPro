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
        
        self.tabifyDockWidget(self.ui_dockWidget_plot_config, self.ui_dockWideget_var)
        
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
        
    
    """ *************************************************************** """
    """ INDICATION: MODIFY THE FOLLOWING CODE UNTIL INDICATED IF NEEDED """
    """ *************************************************************** """
    
    """    Menu and Actions    """       
    def creat_menuBar(self):
        menuBar = QtWidgets.QMenuBar(self)
        
        # Top Menu
        FileMenu = menuBar.addMenu("&File")
        processMenu = menuBar.addMenu("&Process")
        analysisMenu = menuBar.addMenu("&Analysis")
        simulateMenu = menuBar.addMenu("&Simulate")
        widgetssMenu = menuBar.addMenu("&Widgets")
        optionMenu = menuBar.addMenu("&Options")
        
        # Image Menu
        exportMenu = FileMenu.addMenu("Export")
        exportMenu.addAction(self.exportMainToImage)
        exportMenu.addAction(self.exportSlaveToImage)
        exportMenu.addAction(self.exportMainToClipboard)
        exportMenu.addAction(self.exportSlaveToClipboard)
        makeMovieMenu = FileMenu.addMenu("Make Movie from")
        makeMovieMenu.addAction(self.makeMovieFromMain)
        makeMovieMenu.addAction(self.makeMovieFromSlave)
        
        # Process Menu
        backgdSubtractMenu = processMenu.addMenu("Background Subtract")
        backgdSubtractMenu.addAction(self.backgdSubtract2DPlane)
        backgdSubtractMenu.addAction(self.backgdSubtractPerLine)
        processMenu.addAction(self.cropRegion)
        perfectLatticeMenu = processMenu.addMenu("Perfect Lattice")
        perfectLatticeMenu.addAction(self.perfectLatticeSquare)
        perfectLatticeMenu.addAction(self.perfectLatticeHexagonal)
        processMenu.addAction(self.lfCorrection)
        processMenu.addAction(self.lineCut)
        processMenu.addAction(self.lineCuts)
        fourierFilterMenu = processMenu.addMenu("Fourier Filter")
        fourierFilterMenu.addAction(self.fourierFilterOut)
        fourierFilterMenu.addAction(self.fourierFilterIsolate)
        processMenu.addAction(self.register)
        mathMenu = processMenu.addMenu("Math")
        mathMenu.addAction(self.mathAdd)
        mathMenu.addAction(self.mathSubtract)
        mathMenu.addAction(self.mathMultiply)
        mathMenu.addAction(self.mathMultiplyByConst)
        mathMenu.addAction(self.mathDivide)
        mathMenu.addAction(self.mathDivideByConst)
        mathMenu.addAction(self.mathDivideConstBy)
        mathMenu.addAction(self.integral)
        mathMenu.addAction(self.normalization)
        processMenu.addAction(self.extractOneLayer)
        
        processMenu.addAction(self.imageProcessCustomized)
        
        # Analysis Menu
        analysisMenu.addAction(self.fourierTransform)
        lockIn2DMenu = analysisMenu.addMenu("2D Lock-in")        
        lockIn2DMenu.addAction(self.lockIn2DAmplitudeMap)
        lockIn2DMenu.addAction(self.lockIn2DPhaseMap)
        analysisMenu.addAction(self.rMap)
        analysisMenu.addAction(self.gapMap)
        crossCorrMenu = analysisMenu.addMenu("Cross-Correlation")        
        crossCorrMenu.addAction(self.crossCorrelation)
        crossCorrMenu.addAction(self.statisticCrossCorrelation)
        
        # Simulate Menu
        generateCurveMenu = simulateMenu.addMenu("Generate Curve")
        generateCurveMenu.addAction(self.generateHeavisideCurve)
        generateCurveMenu.addAction(self.generateCircleCurve)
        generateCurveMenu.addAction(self.generateGaussianCurve)
        generateCurveMenu.addAction(self.generateSinusoidalCurve)
        generateLatticeMenu = simulateMenu.addMenu("Generate Lattice")
        generateLatticeMenu.addAction(self.generatePerfectLattice)
        generateLatticeMenu.addAction(self.generateLatticeWithLineDomainWall)
        generateLatticeMenu.addAction(self.generateLatticeWithPeriodicDistortion)
        
        # Widgets Menu
        widgetssMenu.addAction(self.showVarDockWidget)
        widgetssMenu.addAction(self.showPlot1DDockWidget)
        
        # Options Menu
        optionMenu.addAction(self.preferenceAction)
        
        #
        self.setMenuBar(menuBar)
        
    def creat_statusBar(self):
        self.status_bar = self.statusBar()
        
    def creat_actions(self):
        # Image Menu
        self.exportMainToImage = QtWidgets.QAction("Main to Image",self)
        self.exportSlaveToImage = QtWidgets.QAction("Slave to Image",self)
        self.exportMainToClipboard = QtWidgets.QAction("Main to Clipboard",self)
        self.exportSlaveToClipboard = QtWidgets.QAction("Slave to Clipboard",self)
        self.makeMovieFromMain = QtWidgets.QAction("Main",self)
        self.makeMovieFromSlave = QtWidgets.QAction("Slave",self)
        
        # Process Menu
        self.backgdSubtract2DPlane = QtWidgets.QAction("2D Plane",self)
        self.backgdSubtractPerLine = QtWidgets.QAction("per line",self)
        self.cropRegion = QtWidgets.QAction("Crop Region",self)
        self.perfectLatticeSquare = QtWidgets.QAction("Square",self)
        self.perfectLatticeHexagonal = QtWidgets.QAction("Hexagonal",self)
        self.lfCorrection = QtWidgets.QAction("LF Correction",self)
        self.lineCut = QtWidgets.QAction('Line Cut',self)
        self.lineCuts = QtWidgets.QAction('Line Cuts',self)
        self.fourierFilterOut = QtWidgets.QAction("Filter Out",self)
        self.fourierFilterIsolate = QtWidgets.QAction("Isolate",self)
        self.register = QtWidgets.QAction("Register",self)
        self.mathAdd = QtWidgets.QAction("m+s",self)
        self.mathSubtract = QtWidgets.QAction("m-s",self)
        self.mathMultiply = QtWidgets.QAction("m*s",self)
        self.mathMultiplyByConst = QtWidgets.QAction("m*const.",self)
        self.mathDivide = QtWidgets.QAction("m/s",self)
        self.mathDivideByConst = QtWidgets.QAction("m/const.",self)
        self.mathDivideConstBy = QtWidgets.QAction("const./m",self)
        self.integral = QtWidgets.QAction("Integral",self)
        self.normalization = QtWidgets.QAction("Normalization",self)
        self.extractOneLayer = QtWidgets.QAction("Extract one layer",self)
        
        self.imageProcessCustomized = QtWidgets.QAction("Customized Algorithm",self)
        
        # Analysis Menu
        self.fourierTransform = QtWidgets.QAction("Fourier Transform",self)
        self.lockIn2DAmplitudeMap = QtWidgets.QAction("Amplitude Map",self)
        self.lockIn2DPhaseMap = QtWidgets.QAction("Phase Map",self)
        self.rMap = QtWidgets.QAction("R-Map",self)
        self.gapMap = QtWidgets.QAction("Gap-Map",self)
        self.crossCorrelation = QtWidgets.QAction('Cross Correlation',self)
        self.statisticCrossCorrelation = QtWidgets.QAction('Statistic Cross Correlation',self)
        
        # Points Menu
        self.setBraggPeaks = QtWidgets.QAction("Set Bragg Peaks",self)
        self.setFilterPoints = QtWidgets.QAction("Set Filter Points",self)
        self.setLockInPoints = QtWidgets.QAction("Set 2D Lock-in Points",self)
        self.setLineCutPoints = QtWidgets.QAction("Set Line Cut Points",self)
        self.setRegisterPointsFromMain = QtWidgets.QAction("Set Register Points from Main",self)
        self.setRegisterPointsFromSlave = QtWidgets.QAction("Set Register Reference Points from Slave",self)
        
        # Simulate Menu
        self.generateHeavisideCurve = QtWidgets.QAction("Heaviside2D")
        self.generateCircleCurve = QtWidgets.QAction("Circle2D",self)
        self.generateGaussianCurve = QtWidgets.QAction("Gaussian2D",self)
        self.generateSinusoidalCurve = QtWidgets.QAction("Sinusoidal2D",self)
        self.generatePerfectLattice = QtWidgets.QAction("Perfect Lattice",self)
        self.generateLatticeWithLineDomainWall = QtWidgets.QAction("Lattice with Line Domain Wall",self)
        self.generateLatticeWithPeriodicDistortion = QtWidgets.QAction("Lattice with Periodic Distortions",self)
        
        # Widgets Menu
        self.showVarDockWidget = QtWidgets.QAction("Variables DockWidget",self)
        self.showPlot1DDockWidget = QtWidgets.QAction("Plot1D DockWidget",self)
        
        # Option Menu
        self.preferenceAction = QtWidgets.QAction("Preference",self)
        
    def connect_actions(self):
        pass
        
    """   Slots for Menu Actions   """ 
  