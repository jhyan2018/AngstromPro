# -*- coding: utf-8 -*-
"""
Created on Tue Apr 16 12:07:04 2024

@author: jiahaoYan
"""

"""
System modules
"""
import os

"""
Third-party Modules
"""
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, pyqtSignal
import matplotlib.pyplot as plt

"""
User Modules
"""
from .ColorBar import ColorBar
from .customizedWidgets.SimplifiedNumberLineEditor import SimplifiedNumberLineEditor
"""
Modules Definition
"""

class PreferenceI2U3(QtWidgets.QMainWindow):
    save_settings = pyqtSignal()
    settings_changed = pyqtSignal(int)
    
    def __init__(self,title='', *args, **kwargs):
        super(PreferenceI2U3, self).__init__(*args, **kwargs)        
        self.setWindowTitle(title)
        self.initUiMembers()
        self.initUiLayout()
        
    def setSettings(self, settings):
        self.settings = settings
        
        # palette
        ccmap = self.settings['COLORMAP']['cmap_palette_list'].split(',')
        self.ui_lw_chosen_cmp_list.addItems(ccmap)
        
        # sync
        self.ui_cb_sync_picked_points.setChecked(self.settings['SYNC']['picked_points'] in ['True'])
        self.ui_cb_sync_rt_points.setChecked(self.settings['SYNC']['real_time_cursor'] in ['True'])
        self.ui_cb_sync_layer.setChecked( self.settings['SYNC']['layer'] in ['True'])
        self.ui_cb_sync_canvas_zoom.setChecked( self.settings['SYNC']['canvas_view_zoom'] in ['True'])
        
        # lock
        self.ui_cb_fixed_data_scale_main.setChecked( self.settings['LOCK']['data_scale_fixed_main'] in ['True'])
        self.ui_cb_fixed_data_scale_slave.setChecked(self.settings['LOCK']['data_scale_fixed_slave'] in ['True'])
        # factor
        self.ui_sl_sigma.setSNText(self.settings['FACTOR']['sigma'])
        self.ui_sl_fft_auto_scale_factor.setSNText(self.settings['FACTOR']['fft_auto_scale_factor'])
        self.ui_sl_slder_zoom_factor.setSNText(self.settings['FACTOR']['slider_scale_zoom_factor'])
        
        # canvas
        self.ui_sl_canvas_size.setSNText(self.settings['CANVAS']['canvas_size_factor'])
        self.ui_cb_bias_text.setChecked(self.settings['CANVAS']['bias_text'] in ['True'])

    def initUiMembers(self):
        self.resize(1000,600)
        # Main widget and layout
        self.ui_centralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.ui_centralWidget)
        self.ui_mainLayout = QtWidgets.QHBoxLayout(self.ui_centralWidget)

        # Side panel for options
        self.ui_optionList = QtWidgets.QListWidget()
        self.ui_optionList.insertItem(0, "ColorMap")
        self.ui_optionList.insertItem(1, "Main & Auxiliary")
        self.ui_optionList.insertItem(2, "Canvas")
        self.ui_optionList.currentItemChanged.connect(self.changePage)
        self.ui_pb_save_settings = QtWidgets.QPushButton('Save Settings')
        self.ui_pb_save_settings.clicked.connect(self.saveSettings)
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.addWidget(self.ui_optionList)
        v_layout.addWidget(self.ui_pb_save_settings)
        self.ui_mainLayout.addLayout(v_layout)

        # Stack of widgets for different pages
        self.ui_pages = QtWidgets.QStackedWidget()
        self.ui_setupPageColorMap()
        self.ui_setupPageMainAndSlave()
        self.ui_setupPageCanvas()
        self.ui_pages.addWidget(self.ui_page_colormap)
        self.ui_pages.addWidget(self.ui_page_main_and_slave)
        self.ui_pages.addWidget(self.ui_page_canvas)
        self.ui_mainLayout.addWidget(self.ui_pages)

    def ui_setupPageColorMap(self):
        self.ui_page_colormap = QtWidgets.QWidget()
        
        self.ui_lw_cmp_list = QtWidgets.QListWidget()
        # Built-in color map
        self.mpt_builtin_cmp_list = plt.colormaps()        
        # Customized color map
        self.mpt_customized_cmp_list = []
        self.customizedColorPalletFolder = './ScienceY/GUI/customizedColorPallets/'
        self.customizedColorFiles = [entry.name for entry in os.scandir(self.customizedColorPalletFolder) if entry.is_file()]
        for cn in self.customizedColorFiles:
            self.mpt_customized_cmp_list.append(cn.split('.')[0])
        
        self.ui_cb_cmp_type = QtWidgets.QComboBox()
        self.ui_cb_cmp_type.addItem('Built-in')
        self.ui_cb_cmp_type.addItem('Customized')
        self.ui_cb_cmp_type.currentIndexChanged.connect(self.colormapListTypeChanged)
        
        self.ui_lw_cmp_list.addItems(self.mpt_builtin_cmp_list)
        
        self.ui_lb_chosen_cmp_list = QtWidgets.QLabel('Chosen Palette')
        self.ui_lw_chosen_cmp_list = QtWidgets.QListWidget()
        
        self.ui_pb_add_to_cmp_chosen_list = QtWidgets.QPushButton('Add ->')
        self.ui_pb_add_to_cmp_chosen_list.clicked.connect(self.addColorMapToChosenList)
        self.ui_pb_remove_from_cmp_chosen_list = QtWidgets.QPushButton('Remove <-')
        self.ui_pb_remove_from_cmp_chosen_list.clicked.connect(self.removeColorMapFromChosenList)
        self.ui_pb_moveup_item_in_chosen_list = QtWidgets.QPushButton('Move Up')
        self.ui_pb_moveup_item_in_chosen_list.clicked.connect(self.moveUpItemInChosenList)
        self.ui_pb_movedown_item_in_chosen_list = QtWidgets.QPushButton('Move Down')
        self.ui_pb_movedown_item_in_chosen_list.clicked.connect(self.moveDownItemInChosenList)
        self.ui_pb_update_chosen_cmap_list = QtWidgets.QPushButton('Update')
        self.ui_pb_update_chosen_cmap_list.clicked.connect(self.updateChosenList)
        self.ui_colorbar_all = ColorBar()
        self.ui_colorbar_chosen = ColorBar()
        self.ui_pb_copy_color_bar = QtWidgets.QPushButton('Clipboard')
        self.ui_pb_copy_color_bar.clicked.connect(self.copyChosenColorbarToClipboard)
        
        self.ui_lw_cmp_list.itemSelectionChanged.connect(self.colormapListActivatedItemChanged)
        self.ui_lw_chosen_cmp_list.itemSelectionChanged.connect(self.chosenColormapListActivatedItemChanged)
        
    def ui_setupPageMainAndSlave(self):
        self.ui_page_main_and_slave = QtWidgets.QWidget()
        
        self.ui_gb_sync = QtWidgets.QGroupBox('Sync')
        self.ui_cb_sync_picked_points = QtWidgets.QCheckBox("Picked Points")
        self.ui_cb_sync_picked_points.stateChanged.connect(self.setSyncPickedPoints)
        self.ui_cb_sync_rt_points = QtWidgets.QCheckBox("Cursor")
        self.ui_cb_sync_rt_points.stateChanged.connect(self.setSyncRtPoints)
        self.ui_cb_sync_layer = QtWidgets.QCheckBox("Layer")
        self.ui_cb_sync_layer.stateChanged.connect(self.setSyncLayer)
        self.ui_cb_sync_canvas_zoom = QtWidgets.QCheckBox("FOV Zoom In/Out")
        self.ui_cb_sync_canvas_zoom.stateChanged.connect(self.setSyncCanvasZoom)

        
        self.ui_gb_lock = QtWidgets.QGroupBox('Lock')
        self.ui_cb_fixed_data_scale_main = QtWidgets.QCheckBox("Fixed Data Scale Main")
        self.ui_cb_fixed_data_scale_main.stateChanged.connect(self.setLockFixedDataScaleMain)
        self.ui_cb_fixed_data_scale_slave = QtWidgets.QCheckBox("Fixed Data Scale Auxiliary")
        self.ui_cb_fixed_data_scale_slave.stateChanged.connect(self.setLockFixedDataScaleSlave)
        
        self.ui_gb_coefficient = QtWidgets.QGroupBox('Coefficient')
        self.ui_lb_sigma = QtWidgets.QLabel('Sigma:')
        self.ui_sl_sigma = SimplifiedNumberLineEditor()
        self.ui_sl_sigma.validTextChanged.connect(self.setFactorSigma)
        self.ui_lb_fft_auto_scale_factor = QtWidgets.QLabel('FFT Image Auto Scale:')
        self.ui_sl_fft_auto_scale_factor = SimplifiedNumberLineEditor()
        self.ui_sl_fft_auto_scale_factor.validTextChanged.connect(self.setFactorFFTImageAutoScale)
        self.ui_lb_slider_zoom_factor = QtWidgets.QLabel('Slier Zoom In/Out:')
        self.ui_sl_slder_zoom_factor = SimplifiedNumberLineEditor()
        self.ui_sl_slder_zoom_factor.validTextChanged.connect(self.setFactorSliderZoom)

    def ui_setupPageCanvas(self):
        self.ui_page_canvas = QtWidgets.QWidget()
        self.ui_lb_canvas_size = QtWidgets.QLabel('Canvas size:')
        self.ui_sl_canvas_size = SimplifiedNumberLineEditor()
        self.ui_sl_canvas_size.validTextChanged.connect(self.setCanvasSizeFactor)
        
        self.ui_cb_bias_text = QtWidgets.QCheckBox("Show Bias Value")
        self.ui_cb_bias_text.stateChanged.connect(self.setBisaText)
        
    def initUiLayout(self):
        self.initLayoutPageColormap()
        self.initLayoutPageMainSlave()
        self.initLayoutPageCanvas()  

    def initLayoutPageColormap(self):
        #Page ColorMap
        v_layout1 = QtWidgets.QVBoxLayout()
        v_layout1.addWidget(self.ui_cb_cmp_type)
        v_layout1.addWidget(self.ui_lw_cmp_list)
        v_layout2 = QtWidgets.QVBoxLayout()
        v_layout2.addWidget(self.ui_pb_add_to_cmp_chosen_list)
        v_layout2.addWidget(self.ui_pb_moveup_item_in_chosen_list)
        v_layout2.addWidget(self.ui_pb_movedown_item_in_chosen_list)
        v_layout2.addWidget(self.ui_pb_remove_from_cmp_chosen_list)
        v_layout2.addWidget(self.ui_pb_update_chosen_cmap_list)
        v_layout2.addWidget(self.ui_pb_copy_color_bar)
        v_layout3 = QtWidgets.QVBoxLayout()
        v_layout3.addWidget(self.ui_lb_chosen_cmp_list)
        v_layout3.addWidget(self.ui_lw_chosen_cmp_list)  
        h_layout1 = QtWidgets.QHBoxLayout()
        h_layout1.addLayout(v_layout1)
        h_layout1.addWidget(self.ui_colorbar_all)
        h_layout1.addLayout(v_layout2)
        h_layout1.addLayout(v_layout3)
        h_layout1.addWidget(self.ui_colorbar_chosen)
        self.ui_page_colormap.setLayout(h_layout1)
        
    def initLayoutPageMainSlave(self):
        #Main&Slave
        gbLayout1 = QtWidgets.QVBoxLayout()
        gbLayout1.addWidget(self.ui_cb_sync_picked_points)
        gbLayout1.addWidget(self.ui_cb_sync_rt_points)
        gbLayout1.addWidget(self.ui_cb_sync_layer)
        gbLayout1.addWidget(self.ui_cb_sync_canvas_zoom)
        self.ui_gb_sync.setLayout(gbLayout1)
        
        gbLayout2 = QtWidgets.QVBoxLayout()
        gbLayout2.addWidget(self.ui_cb_fixed_data_scale_main)
        gbLayout2.addWidget(self.ui_cb_fixed_data_scale_slave)
        self.ui_gb_lock.setLayout(gbLayout2)
        
        gbLayout3 = QtWidgets.QVBoxLayout()
        c_h_layout1 = QtWidgets.QHBoxLayout()
        c_h_layout1.addWidget(self.ui_lb_sigma)
        c_h_layout1.addWidget(self.ui_sl_sigma)
        c_h_layout2 = QtWidgets.QHBoxLayout()
        c_h_layout2.addWidget(self.ui_lb_fft_auto_scale_factor)
        c_h_layout2.addWidget(self.ui_sl_fft_auto_scale_factor)
        c_h_layout3 = QtWidgets.QHBoxLayout()
        c_h_layout3.addWidget(self.ui_lb_slider_zoom_factor)
        c_h_layout3.addWidget(self.ui_sl_slder_zoom_factor)
        gbLayout3.addLayout(c_h_layout1)
        gbLayout3.addLayout(c_h_layout2)
        gbLayout3.addLayout(c_h_layout3)
        self.ui_gb_coefficient.setLayout(gbLayout3)
        
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.ui_gb_sync)
        layout.addWidget(self.ui_gb_lock)
        layout.addWidget(self.ui_gb_coefficient)
        self.ui_page_main_and_slave.setLayout(layout)
        
    def initLayoutPageCanvas(self):
        #Canvas
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.addWidget(self.ui_lb_canvas_size)
        h_layout.addWidget(self.ui_sl_canvas_size)
        
        h_Layout2 = QtWidgets.QVBoxLayout()
        h_Layout2.addWidget(self.ui_cb_bias_text)
        
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(h_layout)
        layout.addLayout(h_Layout2)
        
        self.ui_page_canvas.setLayout(layout)
        
    """ @SLOT"""    
    def saveSettings(self):
        self.save_settings.emit()
        
    def changePage(self, current, previous):
        if current:
            self.ui_pages.setCurrentIndex(self.ui_optionList.row(current))
    
    # Color Map
    def colormapListTypeChanged(self):
        self.ui_lw_cmp_list.itemSelectionChanged.disconnect()
        
        if self.ui_cb_cmp_type.currentIndex() == 0:
            self.ui_lw_cmp_list.clear()
            self.ui_lw_cmp_list.addItems(self.mpt_builtin_cmp_list)
        else:
            self.ui_lw_cmp_list.clear()
            self.ui_lw_cmp_list.addItems(self.mpt_customized_cmp_list)
        
        self.ui_lw_cmp_list.itemSelectionChanged.connect(self.colormapListActivatedItemChanged)
        self.ui_lw_cmp_list.setCurrentRow(0)
        
    def colormapListActivatedItemChanged(self):
        item_row = self.ui_lw_cmp_list.currentRow()
        cmap = self.ui_lw_cmp_list.item(item_row).text()
        ctype = self.ui_cb_cmp_type.currentIndex()
        self.ui_colorbar_all.setColorMap(cmap, ctype)
    
    def chosenColormapListActivatedItemChanged(self):
        item_row = self.ui_lw_chosen_cmp_list.currentRow()
        cmap = self.ui_lw_chosen_cmp_list.item(item_row).text()
        if cmap in self.mpt_builtin_cmp_list:
            ctype = 0 #built-in
        else:
            ctype = 1 #customized
        self.ui_colorbar_chosen.setColorMap(cmap, ctype)
        
    def addColorMapToChosenList(self):
        item_row = self.ui_lw_cmp_list.currentRow()
        item_text = self.ui_lw_cmp_list.item(item_row).text()
        chosen_cmap_list = []
        for index in range(self.ui_lw_chosen_cmp_list.count()):
            chosen_cmap_list.append(self.ui_lw_chosen_cmp_list.item(index).text())
        if not item_text in chosen_cmap_list:
            self.ui_lw_chosen_cmp_list.addItem(item_text)
        
    def removeColorMapFromChosenList(self):
        item_row = self.ui_lw_chosen_cmp_list.currentRow()
        if self.ui_lw_chosen_cmp_list.count() > 1:
            self.ui_lw_chosen_cmp_list.takeItem(item_row)
    
    def moveUpItemInChosenList(self):
        item_row = self.ui_lw_chosen_cmp_list.currentRow()
        itemText = self.ui_lw_chosen_cmp_list.item(item_row).text()
        if item_row > 0:
            upperItemText = self.ui_lw_chosen_cmp_list.item(item_row-1).text()
            self.ui_lw_chosen_cmp_list.item(item_row-1).setText(itemText)
            self.ui_lw_chosen_cmp_list.item(item_row).setText(upperItemText)
            self.ui_lw_chosen_cmp_list.setCurrentRow(item_row-1)      
    
    def moveDownItemInChosenList(self):
        item_row = self.ui_lw_chosen_cmp_list.currentRow()
        itemText = self.ui_lw_chosen_cmp_list.item(item_row).text()
        itemCnt = self.ui_lw_chosen_cmp_list.count()
        
        if item_row < itemCnt - 1:
            lowerItemText = self.ui_lw_chosen_cmp_list.item(item_row+1).text()
            self.ui_lw_chosen_cmp_list.item(item_row+1).setText(itemText)
            self.ui_lw_chosen_cmp_list.item(item_row).setText(lowerItemText)
            self.ui_lw_chosen_cmp_list.setCurrentRow(item_row+1) 
    
    def updateChosenList(self):
        chosen_cmap_list = []
        for index in range(self.ui_lw_chosen_cmp_list.count()):
            chosen_cmap_list.append(self.ui_lw_chosen_cmp_list.item(index).text())
        
        separator = ','
        self.settings['COLORMAP']['cmap_palette_list'] = separator.join(chosen_cmap_list)
        self.settings_changed.emit(1) # Settings Type = 1, 'PALETTE_LIST'
    
    def copyChosenColorbarToClipboard(self):
        self.ui_colorbar_chosen.copyToClipboard()
        
    # Main&Slave
    def setSyncPickedPoints(self):
        if self.ui_cb_sync_picked_points.isChecked():
            self.settings['SYNC']['picked_points']  = 'True'
        else:
            self.settings['SYNC']['picked_points']  = 'False'       
        self.settings_changed.emit(2) # Settings Type = 2, 'SYNC_PICKED_POINTS'
    
    def setSyncRtPoints(self):
        if self.ui_cb_sync_rt_points.isChecked():
            self.settings['SYNC']['real_time_cursor'] = 'True'
            if not self.ui_cb_sync_canvas_zoom.isChecked():
                self.ui_cb_sync_canvas_zoom.setChecked(True)
        else:
            self.settings['SYNC']['real_time_cursor'] = 'False'
            if self.ui_cb_sync_canvas_zoom.isChecked():
                self.ui_cb_sync_canvas_zoom.setChecked(False)
        self.settings_changed.emit(3) # Settings Type = 3, 'SYNC_RT_POINTS'
    
    def setSyncLayer(self):
        if self.ui_cb_sync_layer.isChecked():
            self.settings['SYNC']['layer'] = 'True'
        else:
            self.settings['SYNC']['layer'] = 'False'
        self.settings_changed.emit(4) # Settings Type = 4, 'SYNC_LAYER'
    
    def setSyncCanvasZoom(self):
        if self.ui_cb_sync_canvas_zoom.isChecked():
            self.settings['SYNC']['canvas_view_zoom'] = 'True'
            if not self.ui_cb_sync_rt_points.isChecked():
                self.ui_cb_sync_rt_points.setChecked(True)
        else:
            self.settings['SYNC']['canvas_view_zoom'] = 'False'
            if self.ui_cb_sync_rt_points.isChecked():
                self.ui_cb_sync_rt_points.setChecked(False)
        self.settings_changed.emit(5) # Settings Type = 5, 'SYNC_CANVAS_ZOOM'
        
    def setLockFixedDataScaleMain(self):
        if self.ui_cb_fixed_data_scale_main.isChecked():
            self.settings['LOCK']['data_scale_fixed_main'] = 'True'
        else:
            self.settings['LOCK']['data_scale_fixed_main'] = 'False'
        self.settings_changed.emit(6) # Settings Type = 6, 'LOCK_FIXED_DATA_SCALE_MAIN'

    def setLockFixedDataScaleSlave(self):
        if self.ui_cb_fixed_data_scale_slave.isChecked():
            self.settings['LOCK']['data_scale_fixed_slave'] = 'True'
        else:
            self.settings['LOCK']['data_scale_fixed_slave'] = 'False'
        self.settings_changed.emit(7) # Settings Type = 7, 'LOCK_FIXED_DATA_SCALE_SLAVE'
        
    def setFactorSigma(self):
        self.settings['FACTOR']['sigma'] = self.ui_sl_sigma.snText()
        self.settings_changed.emit(8) # Settings Type = 8, 'FACOTR_SIGMA'
        
    def setFactorFFTImageAutoScale(self):
        self.settings['FACTOR']['fft_auto_scale_factor'] = self.ui_sl_fft_auto_scale_factor.snText()
        self.settings_changed.emit(9) # Settings Type = 9, 'FACOTR_FFT_AUTO_SCALE'
        
    def setFactorSliderZoom(self):
        self.settings['FACTOR']['slider_scale_zoom_factor'] = self.ui_sl_slder_zoom_factor.snText()
        self.settings_changed.emit(10) # Settings Type = 10, 'FACOTR_SLIDER_ZOOM'
    
    def setCanvasSizeFactor(self):
        self.settings['CANVAS']['canvas_size_factor'] = self.ui_sl_canvas_size.snText()
        self.settings_changed.emit(11) # Settings Type = 11, 'FACTOR_CANVAS_SIZE'
        
    def setBisaText(self):
        if self.ui_cb_bias_text.isChecked():
            self.settings['CANVAS']['bias_text'] = 'True'
        else:
            self.settings['CANVAS']['bias_text'] = 'False'
        self.settings_changed.emit(12) # Settings Type = 12, 'BIAS_TEXT'
        