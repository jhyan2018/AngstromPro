# -*- coding: utf-8 -*-
"""
Created on Sun Jul 30 22:16:35 2023

@author: Jiahao Yan
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
import imageio

"""
User Modules
"""
from ..ImageProcess import ImgProc
from ..ImageSimulate import ImgSimu
from .ProcessParameters import ProcessParameters
from ..ImgProcCustomized import ImgProcCustomized

from .GuiFrame import GuiFrame
from .ImageUdsData2or3DWidget import ImageUdsData2or3DWidget
from .Plot1DWidget import Plot1DWidget


""" *************************************** """
""" DO NOT MODIFY THE REGION UNTIL INDICATED"""
""" *************************************** """

class ImageUdsData2or3D(GuiFrame):
    
    def __init__(self, wtype, index, *args, **kwargs):
        super(ImageUdsData2or3D, self).__init__(wtype, index, *args, **kwargs)        
        
        self.initCcUiMembers()
        self.initCcUiLayout()        
        self.initCcNonUiMembers()       
        self.initCcMenuBar()
        
    """ Initializations"""        
    def initCcUiMembers(self):        
        self.ui_img_widget_main = ImageUdsData2or3DWidget()
        self.ui_img_widget_main.ui_lb_widget_name.setText("<b>--- MAIN ---</b>")
        self.ui_img_widget_main.sendMsgSignal.connect(self.getMsgFromImgMainWidget)
        self.ui_img_widget_main.sendMsgSignal.connect(self.getMouseMoveMsgFromImgMainWidget)
        self.ui_img_widget_main.sendMsgSignal.connect(self.getPickedPointsMsgFromImgMainWidget)
        
        self.ui_img_widget_slave = ImageUdsData2or3DWidget()
        self.ui_img_widget_slave.ui_lb_widget_name.setText("<b>--- SLAVE ---</b>")
        self.ui_img_widget_slave.sendMsgSignal.connect(self.getMsgFromImgSlaveWidget)
        
        # dockWiget Plot1D
        self.ui_dockWidget_plot1D = QtWidgets.QDockWidget()
        self.ui_dockWidget_plot1D_Content = Plot1DWidget()

        self.ui_dockWidget_plot1D.setWidget(self.ui_dockWidget_plot1D_Content)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea , self.ui_dockWidget_plot1D)
        self.ui_dockWidget_plot1D.close()
        
        #
        self.ui_lw_uds_variable_name_list.doubleClicked.connect(self.ui_lw_uds_variable_name_list_doulbeClicked)
        
    def initCcUiLayout(self):
        self.ui_horizontalLayout.addWidget(self.ui_img_widget_main)
        self.ui_horizontalLayout.addWidget(self.ui_img_widget_slave)
        
    def initCcNonUiMembers(self):
        pass        
        
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
                self.ui_img_widget_slave.setCanvasWidgetSize(width, height)
                
    # from child windows
    @QtCore.pyqtSlot(int)
    def getMsgFromImgMainWidget(self, msgTypeIdx):
        
        if self.ui_img_widget_main.msg_type[msgTypeIdx] == 'SELECT_USD_VARIABLE' :
            selected_var_index = self.ui_lw_uds_variable_name_list.currentRow()
            selected_var = self.uds_variable_pt_list[selected_var_index]
            self.ui_img_widget_main.setUdsData(selected_var)
            
            #give uds data to Plot1D dock
            if 'dIdV' in selected_var.name and 'fwd' not in selected_var.name:
                self.ui_dockWidget_plot1D_Content.setDataFromImage2or3D(self.ui_img_widget_main.uds_variable)           
            
            # Check the data is not FFT
            if not selected_var.name.split('_')[-1] == 'fft':
                # Calculate FFT of the data and shown in slave 2or3D image widget
                if not selected_var.name+'_fft' in self.uds_variable_name_list:
                    self.actFourierTransform()
                else:
                    data_fft_index = self.uds_variable_name_list.index(selected_var.name+'_fft')
                    self.ui_lw_uds_variable_name_list.setCurrentRow(data_fft_index)
                    
                self.getMsgFromImgSlaveWidget(self.ui_img_widget_slave.msg_type.index('SELECT_USD_VARIABLE'))
                
                self.ui_lw_uds_variable_name_list.setCurrentRow(selected_var_index)
                
            #
            main_var_name = self.ui_img_widget_main.ui_le_selected_var.text()
            slave_var_name = self.ui_img_widget_slave.ui_le_selected_var.text()            
            for i in range(len(self.uds_variable_name_list)):
                self.uds_variable_name_prefix_list[i] = '  '
                if self.uds_variable_name_list[i] == main_var_name:
                    self.uds_variable_name_prefix_list[i] = 'm'
                if self.uds_variable_name_list[i] == slave_var_name:
                    if self.uds_variable_name_prefix_list[i] == 'm':
                        self.uds_variable_name_prefix_list[i] += 's'
                    else:
                        self.uds_variable_name_prefix_list[i] = 's'
                    
            self.updateVarList() 
        
    def getMouseMoveMsgFromImgMainWidget(self, msgTypeIdx):
        if msgTypeIdx ==1 and 'dIdV' in self.ui_img_widget_main.selected_var_name and 'fwd' not in self.ui_img_widget_main.selected_var_name:
            x = self.ui_img_widget_main.msg_type[1][0]
            y = self.ui_img_widget_main.msg_type[1][1]
            self.ui_dockWidget_plot1D_Content.setXYFromImage2or3D(x,y)
    
    def getPickedPointsMsgFromImgMainWidget(self, msgTypeIdx):
        if msgTypeIdx ==2 and 'dIdV' in self.ui_img_widget_main.selected_var_name and 'fwd' not in self.ui_img_widget_main.selected_var_name:
            picked_points_list = self.ui_img_widget_main.msg_type[2]
            self.ui_dockWidget_plot1D_Content.setPickedPointsListFromImage2or3D(picked_points_list)
            
            
    
    
    
    @QtCore.pyqtSlot(int)
    def getMsgFromImgSlaveWidget(self, msgTypeIdx):
        
        if self.ui_img_widget_slave.msg_type[msgTypeIdx] == 'SELECT_USD_VARIABLE' :
            selected_var_index = self.ui_lw_uds_variable_name_list.currentRow()
            selected_var = self.uds_variable_pt_list[selected_var_index]
            self.ui_img_widget_slave.setUdsData(selected_var)
            
            #
            main_var_name = self.ui_img_widget_main.ui_le_selected_var.text()
            slave_var_name = self.ui_img_widget_slave.ui_le_selected_var.text()            
            for i in range(len(self.uds_variable_name_list)):
                self.uds_variable_name_prefix_list[i] = '  '
                if self.uds_variable_name_list[i] == main_var_name:
                    self.uds_variable_name_prefix_list[i] = 'm'
                if self.uds_variable_name_list[i] == slave_var_name:
                    if self.uds_variable_name_prefix_list[i] == 'm':
                        self.uds_variable_name_prefix_list[i] += 's'
                    else:
                        self.uds_variable_name_prefix_list[i] = 's'
                    
            self.updateVarList() 
            
    #
    def ui_lw_uds_variable_name_list_doulbeClicked(self):
        self.getMsgFromImgMainWidget(self.ui_img_widget_main.msg_type.index('SELECT_USD_VARIABLE'))
        
        
            
    """ Regular Functions """
    def clearWidgetsContents(self):
        self.ui_img_widget_main.ui_le_img_proc_parameter_list.clear()
        #self.ui_img_widget_main.ui_lw_img_picked_points_list_widgets.clear()
        
        self.ui_img_widget_slave.ui_le_img_proc_parameter_list.clear()
        #self.ui_img_widget_slave.ui_lw_img_picked_points_list_widgets.clear()
    
            
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
        pointsMenu = menuBar.addMenu("Points")
        simulateMenu = menuBar.addMenu("&Simulate")
        widgetssMenu = menuBar.addMenu("&Widgets")
        
        # Image Menu
        exportMenu = FileMenu.addMenu("Export")
        exportMenu.addAction(self.exportMainToImage)
        exportMenu.addAction(self.exportSlaveToImage)
        exportMenu.addAction(self.exportMainToClipboard)
        exportMenu.addAction(self.exportSlaveToClipboard)
        makeMovieMenu = FileMenu.addMenu("Make Movie form")
        makeMovieMenu.addAction(self.makeMovieFromMain)
        makeMovieMenu.addAction(self.makeMovieFromSlave)
        
        # Process Menu
        backgdSubtractMenu = processMenu.addMenu("Background Subtract")
        backgdSubtractMenu.addAction(self.backgdSubtract2DPlane)
        backgdSubtractMenu.addAction(self.backgdSubtractPerLine)
        processMenu.addAction(self.cropRegion)
        processMenu.addAction(self.perfectLattice)
        processMenu.addAction(self.lfCorrection)
        processMenu.addAction(self.lineCut)
        fourierFilterMenu = processMenu.addMenu("Fourier Filter")
        fourierFilterMenu.addAction(self.fourierFilterOut)
        fourierFilterMenu.addAction(self.fourierFilterIsolate)
        mathMenu = processMenu.addMenu("Math")
        mathMenu.addAction(self.mathAdd)
        mathMenu.addAction(self.mathSubtract)
        mathMenu.addAction(self.mathMultiply)
        mathMenu.addAction(self.mathDivide)
        
        processMenu.addAction(self.imageProcessCustomized)

        
        # Analysis Menu
        analysisMenu.addAction(self.fourierTransform)
        lockIn2DMenu = analysisMenu.addMenu("2D Lock-in")        
        lockIn2DMenu.addAction(self.lockIn2DAmplitudeMap)
        lockIn2DMenu.addAction(self.lockIn2DPhaseMap)
        analysisMenu.addAction(self.rMap)
        analysisMenu.addAction(self.gapMap)
        
        # Points Menu
        pointsMenu.addAction(self.setBraggPeaks)
        pointsMenu.addAction(self.setFilterPoints)
        pointsMenu.addAction(self.setLockInPoints)
        pointsMenu.addAction(self.setLineCutPoints)
        
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
        self.perfectLattice = QtWidgets.QAction("Perfect Lattice",self)
        self.lfCorrection = QtWidgets.QAction("LF Correction",self)
        self.lineCut = QtWidgets.QAction('Line Cut',self)
        self.fourierFilterOut = QtWidgets.QAction("Filter Out",self)
        self.fourierFilterIsolate = QtWidgets.QAction("Isolate",self)
        self.mathAdd = QtWidgets.QAction("+",self)
        self.mathSubtract = QtWidgets.QAction("-",self)
        self.mathMultiply = QtWidgets.QAction("*",self)
        self.mathDivide = QtWidgets.QAction("/",self)
        
        self.imageProcessCustomized = QtWidgets.QAction("Customized Algorithm",self)
        
        # Analysis Menu
        self.fourierTransform = QtWidgets.QAction("Fourier Transform",self)
        self.lockIn2DAmplitudeMap = QtWidgets.QAction("Amplitude Map",self)
        self.lockIn2DPhaseMap = QtWidgets.QAction("Phase Map",self)
        self.rMap = QtWidgets.QAction("R-Map",self)
        self.gapMap = QtWidgets.QAction("Gap-Map",self)
        
        # Points Menu
        self.setBraggPeaks = QtWidgets.QAction("Set Bragg Peaks",self)
        self.setFilterPoints = QtWidgets.QAction("Set Filter Points",self)
        self.setLockInPoints = QtWidgets.QAction("Set 2D Lock-in Points",self)
        self.setLineCutPoints = QtWidgets.QAction("Set Line Cut Points",self)
        
        # Simulate Menu
        self.generateHeavisideCurve = QtWidgets.QAction("Heaviside2D")
        self.generateCircleCurve = QtWidgets.QAction("Circle2D",self)
        self.generateGaussianCurve = QtWidgets.QAction("Gaussian2D",self)
        self.generateSinusoidalCurve = QtWidgets.QAction("Sinusoidal2D",self)
        self.generatePerfectLattice = QtWidgets.QAction("Perfect Lattice",self)
        self.generateLatticeWithLineDomainWall = QtWidgets.QAction("Lattice with Line Domain Wall",self)
        self.generateLatticeWithPeriodicDistortion = QtWidgets.QAction("Lattice with Periodic Distortions",self)
        
        # Widgets Menu
        self.showVarDockWidget = QtWidgets.QAction("Variabls DockWidget",self)
        self.showPlot1DDockWidget = QtWidgets.QAction("Plot1D DockWidget",self)
        
    def connect_actions(self):
        # Image Menu
        self.exportMainToImage.triggered.connect(self.actExportMainToImage)
        self.exportSlaveToImage.triggered.connect(self.actExportSlaveToImage)
        self.exportMainToClipboard.triggered.connect(self.actExportMainToClipboard)
        self.exportSlaveToClipboard.triggered.connect(self.actExportSlaveToClipboard)
        self.makeMovieFromMain.triggered.connect(self.actMakeMovieFromMain)
        self.makeMovieFromSlave.triggered.connect(self.actMakeMovieFromSlave)
        # Process Menu
        self.backgdSubtract2DPlane.triggered.connect(self.actBackgdSubtract2DPlane)
        self.backgdSubtractPerLine.triggered.connect(self.actBackgdSubtractPerLine)
        self.cropRegion.triggered.connect(self.actCropRegion)
        self.perfectLattice.triggered.connect(self.actPerfectLattice)
        self.lfCorrection.triggered.connect(self.actLFCorrection)
        self.lineCut.triggered.connect(self.actLineCut)
        self.fourierFilterOut.triggered.connect(self.actFourierFilterOut)
        self.fourierFilterIsolate.triggered.connect(self.actFourierFilterIsolate)
        self.mathAdd.triggered.connect(self.actMathAdd)
        self.mathSubtract.triggered.connect(self.actMathSubtract)
        self.mathMultiply.triggered.connect(self.actMathMultiply)
        self.mathDivide.triggered.connect(self.actMathDivide)
        
        self.imageProcessCustomized.triggered.connect(self.actImageProcessCustomized)
        
        # Analysis Menu
        self.fourierTransform.triggered.connect(self.actFourierTransform)
        self.lockIn2DAmplitudeMap.triggered.connect(self.actLockIn2DAmplitudeMap)
        self.lockIn2DPhaseMap.triggered.connect(self.actLockIn2DPhaseMap)
        self.rMap.triggered.connect(self.actRMap)
        self.gapMap.triggered.connect(self.actGapMap)
        
        # Points Menu
        self.setBraggPeaks.triggered.connect(self.actSetBraggPeaks)
        self.setFilterPoints.triggered.connect(self.actSetFilterPoints)
        self.setLockInPoints.triggered.connect(self.actSetLockInPoints)
        self.setLineCutPoints.triggered.connect(self.actSetLineCutPoints)
        
        # Simulate Menu
        self.generateHeavisideCurve.triggered.connect(self.actGenerateHeavisideCurve)
        self.generateCircleCurve.triggered.connect(self.actGenerateCircleCurve)
        self.generateGaussianCurve.triggered.connect(self.actGenerateGaussianCurve)
        self.generateSinusoidalCurve.triggered.connect(self.actGenerateSinusoidalCurve)
        self.generatePerfectLattice.triggered.connect(self.actGeneratePerfectLattice)
        self.generateLatticeWithLineDomainWall.triggered.connect(self.actGenerateLatticeWithLineDomainWall)
        self.generateLatticeWithPeriodicDistortion.triggered.connect(self.actGenerateLatticeWithPeriodicDistortions)
        
        #window
        self.showVarDockWidget.triggered.connect(self.actShowVarDockWidget)
        self.showPlot1DDockWidget.triggered.connect(self.actShowPlot1DDockWidget)
    
    """   Slots for Menu Actions   """ 
    # Image Menu
    def actExportMainToImage(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Image', "", "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*)")
        if file_path:
            self.ui_img_widget_main.static_canvas.figure.savefig(file_path)
            
    def actExportSlaveToImage(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Image', "", "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*)")
        if file_path:
            self.ui_img_widget_slave.static_canvas.figure.savefig(file_path)
    
    def actExportMainToClipboard(self):
        pixmap = QtGui.QPixmap(self.ui_img_widget_main.static_canvas.size())
        self.ui_img_widget_main.static_canvas.render(pixmap)
        QtWidgets.QApplication.clipboard().setPixmap(pixmap)
        
    def actExportSlaveToClipboard(self):
        pixmap = QtGui.QPixmap(self.ui_img_widget_slave.static_canvas.size())
        self.ui_img_widget_slave.static_canvas.render(pixmap)
        QtWidgets.QApplication.clipboard().setPixmap(pixmap)
        
    def actMakeMovieFromMain(self):
        self.ui_img_widget_main.imageLayerChangedSlotDisconnect()
        
        #
        frames = []
        layers = self.ui_img_widget_main.ui_sb_image_layers.maximum()
        for frame_num in range(layers+1):
            self.ui_img_widget_main.ui_sb_image_layers.setValue(frame_num)
            self.ui_img_widget_main.imageLayerChanged()
            
            # This force matplot to update within the loop 
            self.ui_img_widget_main.static_canvas.flush_events()
            
            # Save the plot to a BytesIO object in memory
            buf = BytesIO()
            self.ui_img_widget_main.static_canvas.figure.savefig(buf, format='png')
            buf.seek(0)
            
            # Read the image from the in-memory buffer and append to the list of frames
            frame = imageio.imread(buf)
            frames.append(frame)
            
            buf.close()
                  
        # Write the frames to a video file
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Video', "", "MP4 Video (*.mp4);;All Files (*)")
        if file_path:
            imageio.mimsave(file_path, frames, fps=5)
        
        #
        self.ui_img_widget_main.imageLayerChangedSlotConnect()
        
    def actMakeMovieFromSlave(self):
        self.ui_img_widget_slave.imageLayerChangedSlotDisconnect()
        
        #
        frames = []
        layers = self.ui_img_widget_slave.ui_sb_image_layers.maximum()
        for frame_num in range(layers+1):
            self.ui_img_widget_slave.ui_sb_image_layers.setValue(frame_num)
            self.ui_img_widget_slave.imageLayerChanged()
            
            # This force matplot to update within the loop 
            self.ui_img_widget_slave.static_canvas.flush_events()
            
            # Save the plot to a BytesIO object in memory
            buf = BytesIO()
            self.ui_img_widget_slave.static_canvas.figure.savefig(buf, format='png')
            buf.seek(0)
            
            # Read the image from the in-memory buffer and append to the list of frames
            frame = imageio.imread(buf)
            frames.append(frame)
            
            buf.close()
                  
        # Write the frames to a video file
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Video', "", "MP4 Video (*.mp4);;All Files (*)")
        if file_path:
            imageio.mimsave(file_path, frames, fps=5)
        
        #
        self.ui_img_widget_slave.imageLayerChangedSlotConnect()
    
    # Process Menu
    def actBackgdSubtract2DPlane(self):
        self.status_bar.showMessage("Params(Order=1)",5000)

        ct_var_index = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        order = 1
        if len(params) != 0:
            order = int(params)
        
        # process
        uds_data_processed = ImgProc.ipBackgroundSubtract2D(
                                self.uds_variable_pt_list[ct_var_index], order, '2DPlane') 
        
        # update var list
        self.appendToLocalVarList(uds_data_processed)
        
        #
        self.clearWidgetsContents()
        
    def actBackgdSubtractPerLine(self):
        self.status_bar.showMessage("Params(Order=1)",5000)

        ct_var_index = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        order = 1
        if len(params) != 0:
            order = int(params)
        
        # process
        uds_data_processed = ImgProc.ipBackgroundSubtract2D(
                                self.uds_variable_pt_list[ct_var_index], order, 'PerLine') 
        
        # update var list
        self.appendToLocalVarList(uds_data_processed)
        
        #
        self.clearWidgetsContents()
        
    def actCropRegion(self):
        self.status_bar.showMessage("Params(Crop_cycles=1)",5000)
        
        ct_var_index = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())

        points = len (self.ui_img_widget_main.img_picked_points_list)
        picked_points_c = [] #x
        picked_points_r = [] #y
        if   points > 1:
            for pt in self.ui_img_widget_main.img_picked_points_list:
                picked_points_c.append(int(pt.split(',')[0]))
                picked_points_r.append(int(pt.split(',')[1]))
            c_topLeft = min(picked_points_c)
            r_topLeft = min(picked_points_r)
            c_bottomRight = max(picked_points_c)
            r_bottomRight = max(picked_points_r)
            
            #make points of region to be a square and even
            sideLen = min(c_bottomRight - c_topLeft, r_bottomRight - r_topLeft)
            if not sideLen % 2 == 0:
                sideLen -= 1
            c_bottomRight = c_topLeft + sideLen
            r_bottomRight = r_topLeft + sideLen
            
            # get param list
            params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
            crop_cycles = 1
            if len(params) != 0:
                crop_cycles = int(params)
            
            # process
            for i in range(crop_cycles):
                uds_data_processed = ImgProc.ipCropRegion2D(self.uds_variable_pt_list[ct_var_index],
                                                        r_topLeft, c_topLeft, r_bottomRight-2*i, c_bottomRight-2*i)
                # update var list
                self.appendToLocalVarList(uds_data_processed)
                
                # select cropped data and do fourier transform
                self.ui_lw_uds_variable_name_list_doulbeClicked()
            
        else:
            print("Two Points at least")
            
        #
        self.clearWidgetsContents()
            
    def actPerfectLattice(self):
        ct_var_index = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        
        # process
        uds_data_processed = ImgProc.ipPerfectLattice(self.uds_variable_pt_list[ct_var_index])
        
        # update var list
        self.appendToLocalVarList(uds_data_processed)
        
    def actLFCorrection(self):
        self.status_bar.showMessage("Params(rSigma_ref_a0=10.0, uds3D_displacementField)",5000)
        
        ct_var_index = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        rSigma_ref_a0 = 10.0
        uds3D_displacementField_name = None
        
        if len(params) > 0:
            param_numbers = len(params.split(','))
            if param_numbers > 0:
                rSigma_ref_a0 = float(params.split(',')[0])
            if param_numbers > 1:
                uds3D_displacementField_name = params.split(',')[1]
                
        # Displacement     
        if uds3D_displacementField_name == None:
            uds_data_displacmentField = ImgProc.ipCalculateDisplacementField(self.uds_variable_pt_list[ct_var_index], rSigma_ref_a0)
            
            # update var list
            self.appendToLocalVarList(uds_data_displacmentField)
            
            # process
            df_var_index = self.uds_variable_name_list.index( self.uds_variable_pt_list[ct_var_index].name+'_df' )
            displacementField = self.uds_variable_pt_list[df_var_index].data
            uds_data_processed = ImgProc.ipLFCorrection(self.uds_variable_pt_list[ct_var_index], rSigma_ref_a0, displacementField)        
        else:
            # process
            df_var_index = self.uds_variable_name_list.index(uds3D_displacementField_name)
            displacementField = self.uds_variable_pt_list[df_var_index].data
            uds_data_processed = ImgProc.ipLFCorrection(self.uds_variable_pt_list[ct_var_index], rSigma_ref_a0, displacementField)
            
        # update var list
        self.appendToLocalVarList(uds_data_processed)
        
    def actLineCut(self):
        self.ui_dockWidget_plot1D_Content.setLineCutStartAndEndPoints(self.ui_img_widget_main.uds_variable.info['LineCutPoints'])
    def actFourierFilterOut(self):
        self.status_bar.showMessage("Params(kSigma=1.0)",5000)
        
        ct_var_index = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        kSigma = 1.0
        if len(params) != 0:
            kSigma = float(params.split(',')[0])
        
        # process
        uds_data_processed = ImgProc.ipFourierFilterOut(self.uds_variable_pt_list[ct_var_index], "GAUSSIAN", kSigma)
        
        # update var list
        self.appendToLocalVarList(uds_data_processed)
        
        #
        self.clearWidgetsContents()
    
    def actFourierFilterIsolate(self):
        self.status_bar.showMessage("Params(kSigma=1.0)",5000)
        
        ct_var_index = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        kSigma = 1.0
        if len(params) != 0:
            kSigma = float(params.split(',')[0])
        
        # process
        uds_data_processed = ImgProc.ipFourierFilterIsolate(self.uds_variable_pt_list[ct_var_index], "GAUSSIAN", kSigma)
        
        # update var list
        self.appendToLocalVarList(uds_data_processed)
        
        #
        self.clearWidgetsContents()
    
    def actMathAdd(self):
        ct_var_index_main = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        ct_var_index_slave = self.uds_variable_name_list.index(self.ui_img_widget_slave.ui_le_selected_var.text())
        
        # process
        uds_data_processed = ImgProc.ipMath(self.uds_variable_pt_list[ct_var_index_main], 
                                            self.uds_variable_pt_list[ct_var_index_slave],"+")
        # update var list
        self.appendToLocalVarList(uds_data_processed)
        
        #
        self.clearWidgetsContents()
    
    def actMathSubtract(self):
        ct_var_index_main = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        ct_var_index_slave = self.uds_variable_name_list.index(self.ui_img_widget_slave.ui_le_selected_var.text())
        
        # process
        uds_data_processed = ImgProc.ipMath(self.uds_variable_pt_list[ct_var_index_main], 
                                            self.uds_variable_pt_list[ct_var_index_slave],"-")
        # update var list
        self.appendToLocalVarList(uds_data_processed)
        
        #
        self.clearWidgetsContents()
        
    def actMathMultiply(self):
        ct_var_index_main = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        ct_var_index_slave = self.uds_variable_name_list.index(self.ui_img_widget_slave.ui_le_selected_var.text())
        
        # process
        uds_data_processed = ImgProc.ipMath(self.uds_variable_pt_list[ct_var_index_main], 
                                            self.uds_variable_pt_list[ct_var_index_slave],"*")
        # update var list
        self.appendToLocalVarList(uds_data_processed)
        
        #
        self.clearWidgetsContents()
        
    def actMathDivide(self):
        ct_var_index_main = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        ct_var_index_slave = self.uds_variable_name_list.index(self.ui_img_widget_slave.ui_le_selected_var.text())
        
        # process
        uds_data_processed = ImgProc.ipMath(self.uds_variable_pt_list[ct_var_index_main], 
                                            self.uds_variable_pt_list[ct_var_index_slave],"/")
        # update var list
        self.appendToLocalVarList(uds_data_processed)
        
        #
        self.clearWidgetsContents()
        
    def actImageProcessCustomized(self):
        ct_var_index_main = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        ct_var_index_slave = self.uds_variable_name_list.index(self.ui_img_widget_slave.ui_le_selected_var.text())
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        
        # process
        uds_data_processed = ImgProcCustomized.IPC(self.uds_variable_pt_list[ct_var_index_main], 
                                                   self.uds_variable_pt_list[ct_var_index_slave],
                                                   params)
        # update var list
        self.appendToLocalVarList(uds_data_processed)
        
        #
        self.clearWidgetsContents()
    
    # Analysis Menu
    def actFourierTransform(self):
        ct_var_index = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        
        # analyse
        uds_data_analysed = ImgProc.ipFourierTransform2D(self.uds_variable_pt_list[ct_var_index])
        
        # update var list
        self.appendToLocalVarList(uds_data_analysed) 
        
        #
        self.clearWidgetsContents()
    
    def actLockIn2D(self, MapType, phaseUnwrap=True):
        self.status_bar.showMessage("Params(rSigma_ref_a0=1.0)",5000)
        
        ct_var_index = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        rSigma_ref_a0 = 1.0
        if len(params) != 0:
            rSigma_ref_a0 = float(params.split(',')[0])
            
        # get pixles of Q vector for 2D Lock-in
        for i in range(len(self.uds_variable_pt_list[ct_var_index].info['LockInPoints'])):
            lPx = self.uds_variable_pt_list[ct_var_index].info['LockInPoints'][i][0]
            lPy = self.uds_variable_pt_list[ct_var_index].info['LockInPoints'][i][1]
        
            # analyse
            uds_data_analysed = ImgProc.ipLockIn2D(self.uds_variable_pt_list[ct_var_index], lPx, lPy, rSigma_ref_a0, MapType, phaseUnwrap)
            
            # save corresponding Q vector
            Q_lockin = []
            Q_lockin.append((lPx,lPy))
            uds_data_analysed.info['LockInPoints'] = Q_lockin
            
            # update var list
            self.appendToLocalVarList(uds_data_analysed)
            
        #
        self.clearWidgetsContents()
        
    def actLockIn2DAmplitudeMap(self):
        self.actLockIn2D("Amplitude")
        
        #
        self.clearWidgetsContents()
        
    def actLockIn2DPhaseMap(self):
        self.actLockIn2D("Phase")
        self.actLockIn2D("Phase", False)
                
        #
        self.clearWidgetsContents()

    def actRMap(self):
        ct_var_index = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        
        # analyse
        uds_data_analysed = ImgProc.ipRmap(self.uds_variable_pt_list[ct_var_index])
         
        # update var list
        self.appendToLocalVarList(uds_data_analysed) 
         
        #
        self.clearWidgetsContents()    
        
    def actGapMap(self):
        self.status_bar.showMessage("Params(Order=2)",5000)
        ct_var_index = self.uds_variable_name_list.index(self.ui_img_widget_main.ui_le_selected_var.text())
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        order = 2
        if len(params) != 0:
            order = int(params)
        # process
        uds_data_processed = ImgProc.ipGapMap(
                                self.uds_variable_pt_list[ct_var_index], order) 
        
        # update var list
        self.appendToLocalVarList(uds_data_processed)

        #
        self.clearWidgetsContents()



    
    # Points Menu
    def actSetBraggPeaks(self):     
        var_name = self.ui_img_widget_slave.uds_variable.name[0:-4]
        bp_var_index = self.uds_variable_name_list.index(var_name)
        
        points = len (self.ui_img_widget_slave.img_picked_points_list)
        picked_points = []
        if   points > 1:
            for pt in self.ui_img_widget_slave.img_picked_points_list:
                picked_points.append( (int(pt.split(',')[0]), int(pt.split(',')[1])) )

                
            self.uds_variable_pt_list[bp_var_index].info['BraggPeaks'] = picked_points
            
            #
            if self.ui_img_widget_main.uds_variable.name == self.uds_variable_pt_list[bp_var_index].name:
                self.ui_img_widget_main.uds_variable.info['BraggPeaks'] = picked_points
                self.ui_img_widget_main.updateDataInfo()
                
        #
        self.clearWidgetsContents()
        
    def actSetLineCutPoints(self):
        var_name = self.ui_img_widget_main.uds_variable.name
        bp_var_index = self.uds_variable_name_list.index(var_name)
        
        points = len (self.ui_img_widget_main.img_picked_points_list)
        picked_points = []
        if   points > 1:
            for pt in self.ui_img_widget_main.img_picked_points_list:
                picked_points.append( (int(pt.split(',')[0]), int(pt.split(',')[1])) )

                
            self.uds_variable_pt_list[bp_var_index].info['LineCutPoints'] = picked_points
            
            #
            if self.ui_img_widget_main.uds_variable.name == self.uds_variable_pt_list[bp_var_index].name:
                self.ui_img_widget_main.uds_variable.info['LineCutPoints'] = picked_points
                self.ui_img_widget_main.updateDataInfo()
        
    
    def actSetFilterPoints(self):
        var_name = self.ui_img_widget_slave.uds_variable.name[0:-4]
        ft_var_index = self.uds_variable_name_list.index(var_name)
        
        points = len (self.ui_img_widget_slave.img_picked_points_list)
        picked_points = []
        if   points > 0:
            for pt in self.ui_img_widget_slave.img_picked_points_list:
                picked_points.append( (int(pt.split(',')[0]), int(pt.split(',')[1])) )

                
            self.uds_variable_pt_list[ft_var_index].info['FilterPoints'] = picked_points
            
            #
            if self.ui_img_widget_main.uds_variable.name == self.uds_variable_pt_list[ft_var_index].name:
                self.ui_img_widget_main.uds_variable.info['FilterPoints'] = picked_points
                self.ui_img_widget_main.updateDataInfo()
                
        #
        self.clearWidgetsContents()
                
    def actSetLockInPoints(self):
        var_name = self.ui_img_widget_slave.uds_variable.name[0:-4]
        ft_var_index = self.uds_variable_name_list.index(var_name)
        
        points = len (self.ui_img_widget_slave.img_picked_points_list)
        picked_points = []
        if   points > 0:
            for pt in self.ui_img_widget_slave.img_picked_points_list:
                picked_points.append( (int(pt.split(',')[0]), int(pt.split(',')[1])) )

                
            self.uds_variable_pt_list[ft_var_index].info['LockInPoints'] = picked_points
            
            #
            if self.ui_img_widget_main.uds_variable.name == self.uds_variable_pt_list[ft_var_index].name:
                self.ui_img_widget_main.uds_variable.info['LockInPoints'] = picked_points
                self.ui_img_widget_main.updateDataInfo()
                
        #
        self.clearWidgetsContents()
    
    # Simulate Menu
    def actGenerateHeavisideCurve(self):
        self.status_bar.showMessage("Params(size=512, edge_x=0, edge_y=0 )",5000)
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        p = ProcessParameters('actGenerateHeavisideCurve')
        p.setParameters(params)
        
        #
        uds_data_simulated = ImgSimu.ismGenerateHeaviside2D(p.p[0], p.p[1], p.p[2])
        
        # update var list
        self.appendToLocalVarList(uds_data_simulated)

        #
        self.clearWidgetsContents()
    
    def actGenerateCircleCurve(self):
        self.status_bar.showMessage("Params(size=512, radius=10, center_x=0, center_y=0)",5000)
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        p = ProcessParameters('actGenerateCircleCurve')
        p.setParameters(params)
           
        #
        uds_data_simulated = ImgSimu.ismGenerateCircle2D(p.p[0], p.p[1], p.p[2], p.p[3])
        
        # update var list
        self.appendToLocalVarList(uds_data_simulated)

        #
        self.clearWidgetsContents()             
        
    def actGenerateGaussianCurve(self):
        self.status_bar.showMessage("Params(size=512, sigma=10, center_x=0, center_y=0)",5000)
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        p = ProcessParameters('actGenerateGaussianCurve')
        p.setParameters(params)
            
        #
        uds_data_simulated = ImgSimu.ismGenerateGaussian2D(p.p[0], p.p[1], p.p[2], p.p[3])
        
        # update var list
        self.appendToLocalVarList(uds_data_simulated)
        
        #
        self.clearWidgetsContents()
        
    def actGenerateSinusoidalCurve(self):
        self.status_bar.showMessage("Params(size, qx1, qy1, phase1, qx2 ...)",5000)
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        
        if len(params) > 0:
            param_numbers = len(params.split(','))
            
            size = int(params.split(',')[0])
            qx = []
            qy = []
            phase = []
            
            for i in range( int((param_numbers-1)/3)):
                qx.append( int(params.split(',')[3*i+1]) )
                qy.append( int(params.split(',')[3*i+2]) )
                phase.append( float(params.split(',')[3*i+3]) )
                
            uds_data_simulated = ImgSimu.ismGenerateSinusoidal2D(size, qx, qy, phase)
             
        # update var list
        self.appendToLocalVarList(uds_data_simulated)
        
        #
        self.clearWidgetsContents()
    
    def actGeneratePerfectLattice(self):            
        self.status_bar.showMessage("Params(m=20, n=20, a1x=10, a1y=0, a2x=0, a2y=10, atomSize=None, atomCurve=Gaussian,  Ox=0, Oy=0, p1=1, p2=1)")
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        p = ProcessParameters('actGeneratePerfectLattice')
        p.setParameters(params)
         
        #
        uds_data_simulated = ImgSimu.ismGeneratePerfectLattice2D(p.p[0], p.p[1], p.p[2], p.p[3], p.p[4], p.p[5], 
                                                                 p.p[6], p.p[7], p.p[8], p.p[9], p.p[10], p.p[11])
        
        # update var list
        self.appendToLocalVarList(uds_data_simulated)
        
        #
        self.clearWidgetsContents()
        
    def actGenerateLatticeWithLineDomainWall(self):
        self.status_bar.showMessage("Params(m=20, n=20, a1x=10, a1y=0, a2x=0, a2y=10, atomSize=None, shiftDistance=0.25, atomCurve=Gaussian,  Ox=0, Oy=0)")
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        p = ProcessParameters('actGenerateLatticeWithLineDomainWall')
        p.setParameters(params)
        
        #
        uds_data_simulated = ImgSimu.ismGenerateLattice2DWithLineDomainWall(p.p[0], p.p[1], p.p[2], p.p[3], p.p[4], p.p[5], 
                                                                            p.p[6], p.p[7], p.p[8], p.p[9], p.p[10])
        
        # update var list
        self.appendToLocalVarList(uds_data_simulated)
        
        #
        self.clearWidgetsContents()
        
    def actGenerateLatticeWithPeriodicDistortions(self):
        msg = "Params(m=20, n=20, a1x=10, a1y=0, a2x=0, a2y=10, d1x=40, d1y=0, d2x=0, d2y=0, dpA1=0.25, dpA2=0,"
        msg += "atomSize=None, atomCurve=Gaussian,  Ox=0, Oy=0, dPhi1=0.79, dPhi2=0.79)"
        self.status_bar.showMessage(msg)
        
        # get param list
        params = self.ui_img_widget_main.ui_le_img_proc_parameter_list.text()
        p = ProcessParameters('actGenerateLatticeWithPeriodicDistortions')
        p.setParameters(params)         
                
        #
        uds_data_simulated = ImgSimu.ismGeneratelattice2DWithPeriodicDistortion(p.p[0], p.p[1], p.p[2], p.p[3], p.p[4], p.p[5], 
                                                                                p.p[6], p.p[7], p.p[8], p.p[9], p.p[10], p.p[11],
                                                                                p.p[12], p.p[13], p.p[14], p.p[15], p.p[16], p.p[17])
        
        # update var list
        self.appendToLocalVarList(uds_data_simulated)
        
        #
        self.clearWidgetsContents()
        
    # Widgets Menus
    def actShowVarDockWidget(self):
        self.ui_dockWideget_var.show()
        
    def actShowPlot1DDockWidget(self):
        self.ui_dockWidget_plot1D.show()        
           

        
        
