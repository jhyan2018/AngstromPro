# -*- coding: utf-8 -*-
"""
Created on Mon May 13 16:13:59 2024

@author: jiahao yan
"""

"""
System modules
"""
import ctypes, os

"""
Third-party Modules
"""
import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui

"""
User Modules
"""
from .SnapshotManager import SnapshotInfo

""" *************************************** """
""" DO NOT MODIFY THIS FILE"""
""" *************************************** """

class GalleryContentWidget(QtWidgets.QWidget):
    #sendMsgSignal = QtCore.pyqtSignal(int)
    
    def __init__(self, snapshots_manager, snapshots_info, ch_idx, *args, **kwargs):
        super(GalleryContentWidget, self).__init__( *args, **kwargs)

        self.initNonUiMembers(snapshots_manager, snapshots_info, ch_idx) 
        self.initUiMembers()
        self.initUiLayout()  
        

    
    def initNonUiMembers(self, snapshots_manager, snapshots_info, ch_idx):
        self.snapshots_manager = snapshots_manager
        self.snapshots_info = snapshots_info
        self.ch_idx = ch_idx
        self.ch_layer = int (self.snapshots_info.ch_layers[self.ch_idx])
        self.ch_layer_value = self.snapshots_info.ch_layer_value[self.ch_idx].split(',')
    
    def initUiMembers(self):
        self.ui_lb_png_display = QtWidgets.QLabel()
        self.ui_lb_png_display.setFixedHeight(1000)
        self.ui_lb_png_display.setFixedWidth(1000)
        self.ui_lb_file_path = QtWidgets.QLabel()
        self.ui_lb_channel = QtWidgets.QLabel()
        self.ui_pivotal_info = QtWidgets.QLabel()
        
        self.ui_sb_channel_layers = QtWidgets.QSpinBox()
        self.ui_sb_channel_layers.valueChanged.connect(self.channelLayerChanged)
        if self.ch_layer < 2:
            self.ui_sb_channel_layers.setEnabled(False)
        self.ui_le_channel_layers_v = QtWidgets.QLineEdit()
        self.ui_le_channel_layers_v.setText(self.ch_layer_value[0])
       
        self.ui_sb_channel_layers.setMinimum(0)
        self.ui_sb_channel_layers.setMaximum(self.ch_layer - 1)
        
        self.ui_pb_send_to_gui_manager = QtWidgets.QPushButton('<-Send')
        self.ui_pb_send_to_gui_manager.clicked.connect(self.sendChannelDataToGuiManager)
        
        #
        png_path = os.path.join(self.snapshots_manager.snapshots_dir, self.snapshots_info.ch_uuid[self.ch_idx])
        if not self.snapshots_info.ch_layers[self.ch_idx] == '1':
            png_path = os.path.join(png_path, 'layer0.png')
        pixmap = QtGui.QPixmap(png_path)
        self.setPngDisplayScaledPixmap(pixmap)
        
        #
        self.ui_lb_file_path.setText(self.snapshots_info.src_file_path )
        self.ui_lb_file_path.setWordWrap(True)
        self.ui_lb_channel.setText(self.snapshots_info.channel[self.ch_idx])
    
    def initUiLayout(self):
        layout = QtWidgets.QGridLayout()
        
        ui_verticalLayout1 = QtWidgets.QVBoxLayout()
        ui_verticalLayout1.addWidget(self.ui_lb_file_path)
        ui_verticalLayout1.addWidget(self.ui_lb_channel)
        ui_verticalLayout1.addWidget(self.ui_pivotal_info)
        
        ui_verticalLayout2 = QtWidgets.QVBoxLayout()
        
        ui_verticalLayout3 = QtWidgets.QVBoxLayout()
        ui_horizontalLayout1 = QtWidgets.QHBoxLayout()
        ui_horizontalLayout1.addWidget(self.ui_sb_channel_layers)
        ui_horizontalLayout1.addWidget(self.ui_le_channel_layers_v)
        ui_verticalLayout3.addLayout(ui_horizontalLayout1)
        ui_verticalLayout3.addWidget(self.ui_pb_send_to_gui_manager)
        
        layout.addWidget(self.ui_lb_png_display, 0, 0)
        layout.addLayout(ui_verticalLayout1, 1, 0)
        layout.addLayout(ui_verticalLayout2, 0, 1)
        layout.addLayout(ui_verticalLayout3, 1, 1)
        
        self.setLayout(layout)
        
    """ SLots """
    def channelLayerChanged(self):
        srcfile_path = self.snapshots_info.src_file_path
        src_file_lastmodified = self.snapshots_info.src_file_lastmodified
        channel = self.snapshots_info.channel[self.ch_idx]
        layer = self.ui_sb_channel_layers.value()
        snapshots_info = SnapshotInfo(srcfile_path, src_file_lastmodified)
        
        self.snapshots_manager.generate_snapshots(srcfile_path, src_file_lastmodified, channel, layer, snapshots_info)

        #
        self.setPngDisplayScaledPixmap(snapshots_info.pixmap[0])
        
        self.ui_le_channel_layers_v.setText(self.ch_layer_value[layer])
        
    def sendChannelDataToGuiManager(self):
        pass
    
    """ Regular function"""
    def setPngDisplayScaledPixmap(self, pixmap):
        scaled_pixmap = pixmap.scaled(self.ui_lb_png_display.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
        self.ui_lb_png_display.setPixmap(scaled_pixmap)