# -*- coding: utf-8 -*-
"""
Created on Mon May 13 16:13:59 2024

@author: jiahao yan
"""

"""
System modules
"""
import os, gc
"""
Third-party Modules
"""
from PyQt5 import QtCore, QtWidgets, QtGui

"""
User Modules
"""
from .SnapshotManager import SnapshotInfo


""" *************************************** """
""" DO NOT MODIFY THIS FILE"""
""" *************************************** """

class ImageDisplayWidget(QtWidgets.QWidget):
    def __init__(self, image_path=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image = None
        if image_path:
            self.load_image(image_path)

    def load_image(self, image_path):
        """Load a PNG image into the widget."""
        self.image = QtGui.QImage(image_path)  # Load the image using QImage

        if self.image.isNull():
            print("Failed to load the image.")
        else:
            #self.setMinimumSize(self.image.width(), self.image.height())
            pass

        # Force the widget to repaint with the new image
        self.update()

    def remove_image(self):
        if self.image:
            self.image = None  # Clear the QImage object
            self.update()  # Repaint the widget to clear the display
            
            # Force garbage collection to ensure memory is released
            #gc.collect()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        # Only draw the image if it exists
        if self.image:
            # Optionally, you can scale the image to fit the widget size
            scaled_image = self.image.scaled(self.size(), QtCore.Qt.KeepAspectRatio)
            painter.drawImage(0, 0, scaled_image)

        painter.end()
        
    def resizeEvent(self, event):
        """Handle widget resize to optionally scale the image."""
        self.update()  # Repaint when resized
        super().resizeEvent(event)

class GalleryContentWidget(QtWidgets.QWidget):
    sendChannelDataSignal = QtCore.pyqtSignal(str, str)
    
    def __init__(self, snapshots_manager, snapshots_info, ch_idx, colorbarPixmap, *args, **kwargs):
        super(GalleryContentWidget, self).__init__( *args, **kwargs)

        self.initNonUiMembers(snapshots_manager, snapshots_info, ch_idx, colorbarPixmap) 
        self.initUiMembers()
        self.initUiLayout()  
        

    
    def initNonUiMembers(self, snapshots_manager, snapshots_info, ch_idx, colorbarPixmap):
        
        self.snapshots_manager = snapshots_manager
        self.snapshots_info = snapshots_info
        self.ch_idx = ch_idx

        self.ch_layer = int (self.snapshots_info.ch_layers[self.ch_idx])
        self.ch_layer_value = self.snapshots_info.ch_layer_value[self.ch_idx].split(',')
        if snapshots_info.ch_type[self.ch_idx] == 'IMAGE':
            self.ch_layer_scale = self.snapshots_info.ch_layer_scale[self.ch_idx].split(',')
        self.colorbar_pixmap = colorbarPixmap

        
    def initUiMembers(self):
        #
        self.ui_png_display = ImageDisplayWidget()
        
        #
        self.ui_lb_file_path = QtWidgets.QLineEdit()
        self.ui_lb_channel = QtWidgets.QLabel()
        self.ui_pivotal_info = QtWidgets.QLabel()           

        #
        self.ui_lb_colorbar = QtWidgets.QLabel()
        self.drawColorbar()
        
        self.ui_lb_data_scale_u = QtWidgets.QLabel()
        self.ui_lb_data_scale_l = QtWidgets.QLabel()
        if self.snapshots_info.ch_type[self.ch_idx] == 'IMAGE':
            d_s_u_v = self.ch_layer_scale[1]
            d_s_l_v = self.ch_layer_scale[0]
            self.ui_lb_data_scale_u.setText(d_s_u_v)
            self.ui_lb_data_scale_l.setText(d_s_l_v)
        
        #
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
        self.png_path = os.path.join(self.snapshots_manager.snapshots_dir, self.snapshots_info.ch_uuid[self.ch_idx])
        if not self.snapshots_info.ch_layers[self.ch_idx] == '1':
            self.png_path = os.path.join(self.png_path, 'layer0.png')
        #self.pixmap = QtGui.QPixmap(png_path)
        self.drawPngDisplay()

        #
        self.ui_lb_file_path.setText(self.snapshots_info.src_file_path.split('/')[-1])
        #self.ui_lb_file_path.setTextFormat(QtCore.Qt.PlainText)
        self.ui_lb_channel.setText(self.snapshots_info.channel[self.ch_idx])
        separator = '\n'
        self.ui_pivotal_info.setText(separator.join(self.snapshots_info.pivotal_info)) 

    def initUiLayout(self):
        layout = QtWidgets.QGridLayout()

        ui_verticalLayout1 = QtWidgets.QVBoxLayout()
        ui_verticalLayout1.addWidget(self.ui_lb_file_path)
        ui_verticalLayout1.addWidget(self.ui_lb_channel)
        ui_verticalLayout1.addWidget(self.ui_pivotal_info)
        
        ui_verticalLayout2 = QtWidgets.QVBoxLayout()
        if self.snapshots_info.ch_type[self.ch_idx] == 'IMAGE':
            ui_verticalLayout2.addWidget(self.ui_lb_data_scale_u, alignment=QtCore.Qt.AlignCenter)
            ui_verticalLayout2.addWidget(self.ui_lb_colorbar, alignment=QtCore.Qt.AlignCenter)
            ui_verticalLayout2.addWidget(self.ui_lb_data_scale_l, alignment=QtCore.Qt.AlignCenter)
        
        ui_verticalLayout3 = QtWidgets.QVBoxLayout()
        ui_horizontalLayout1 = QtWidgets.QHBoxLayout()
        ui_horizontalLayout1.addWidget(self.ui_sb_channel_layers)
        ui_horizontalLayout1.addWidget(self.ui_le_channel_layers_v)
        ui_verticalLayout3.addLayout(ui_horizontalLayout1)
        ui_verticalLayout3.addWidget(self.ui_pb_send_to_gui_manager)
        
        

        layout.addWidget(self.ui_png_display, 0, 0)
        layout.addLayout(ui_verticalLayout1, 1, 0)
        layout.addLayout(ui_verticalLayout2, 0, 1)
        layout.addLayout(ui_verticalLayout3, 1, 1)
        
        #
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
        self.pixmap = snapshots_info.pixmap[0]
        self.drawPngDisplay()
        
        self.ui_le_channel_layers_v.setText(self.ch_layer_value[layer])
        
        self.ch_layer_scale = snapshots_info.ch_layer_scale[0].split(',')
        self.ui_lb_data_scale_u.setText(self.ch_layer_scale[0])
        self.ui_lb_data_scale_l.setText(self.ch_layer_scale[1])
        
    def sendChannelDataToGuiManager(self):
        file_path = self.snapshots_info.src_file_path
        channel = self.snapshots_info.channel[self.ch_idx]
        
        self.sendChannelDataSignal.emit(file_path, channel)
        

    """ Regular function"""
    def resize(self, width, height):
        self.setFixedWidth(width)
        self.setFixedHeight(height)       

        # pnd display
        self.ui_png_display.setFixedSize(int(width*0.7), int(height*0.7))
        self.drawPngDisplay()

        # colobar
        self.ui_lb_colorbar.setFixedSize(int(width*0.05), int(height*0.5))
        self.drawColorbar() 
        
        #
        
    def drawPngDisplay(self): 
        #if self.snapshots_info.ch_type[self.ch_idx] == 'IMAGE':
            #scaled_pixmap = self.pixmap.scaled(self.ui_lb_png_display.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.FastTransformation)
        #else:
            #scaled_pixmap = self.pixmap.scaled(self.ui_lb_png_display.size(), QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.FastTransformation)
        
        self.ui_png_display.remove_image()
        self.ui_png_display.load_image(self.png_path)
        
    def setColorbarPixmap(self, pixmap):
        self.colorbar_pixmap = pixmap
    
    def drawColorbar(self):                
        scaled_pixmap = self.colorbar_pixmap.scaled(self.ui_lb_colorbar.size(), QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
        #self.ui_lb_colorbar.setPixmap(scaled_pixmap)