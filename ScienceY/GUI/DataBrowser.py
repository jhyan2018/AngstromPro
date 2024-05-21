# -*- coding: utf-8 -*-
"""
Created on Sat May  4 11:41:36 2024

@author: jiahaoYan
"""

"""
System modules
"""
import os
"""
Third-party Modules
"""
import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QFileInfo
"""
User Modules
"""
from .GuiFrame import GuiFrame
from .FileSystemTree import FileSystemTree
from .SnapshotManager import SnapshotManager, SnapshotInfo
from .GalleryContentWidget import GalleryContentWidget
from .ConfigManager import ConfigManager
from .ColorBar import ColorBar
from .customizedWidgets.DockWidget import DockWidget
from .customizedWidgets.ScrollArea import ScrollArea

""" *************************************** """
""" DO NOT MODIFY THE REGION UNTIL INDICATED"""
""" *************************************** """
class GalleryViewManager(QtWidgets.QWidget):
    viewChangedSignal = QtCore.pyqtSignal(int)
    filterSelectionChangedSignal = QtCore.pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        super(GalleryViewManager, self).__init__( *args, **kwargs)
        self.initUiMembers()
        self.initNonUiMembers()
        self.initUiLayout()
    
    def initUiMembers(self):
        self.ui_lb_view = QtWidgets.QLabel('View:')
        self.ui_cb_view = QtWidgets.QComboBox()
        self.ui_cb_view.addItem('2 / row')
        self.ui_cb_view.addItem('3 / row')
        self.ui_cb_view.setCurrentIndex(1)
        self.ui_cb_view.currentIndexChanged.connect(self.view_changed)
        
        self.ui_lb_channel_filter = QtWidgets.QLabel('Channel Filter:')
        self.ui_channel_filter = ScrollArea()
    
    def initNonUiMembers(self):
        self.gallery_filter = {}
        self.gallery_filter_bool= {}
        self.gallery_filter_checkboxes = []
    
    def initUiLayout(self):
        ui_layout = QtWidgets.QVBoxLayout()
        ui_layout.addWidget(self.ui_lb_view)
        ui_layout.addWidget(self.ui_cb_view)
        
        ui_layout.addWidget(self.ui_lb_channel_filter)
        ui_layout.addWidget(self.ui_channel_filter)
        self.setLayout(ui_layout)
        
    def set_gallery_filter(self, gallery_filter):
        self.gallery_filter = gallery_filter
        self.gallery_filter_bool= {}
        self.gallery_filter_checkboxes = []
        
        ch_filter_content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        
        #
        for suffix, channels in self.gallery_filter.items():
            self.gallery_filter_bool[suffix] = []
            for channel in channels:
                ui_cbx = QtWidgets.QCheckBox(suffix + '-' + channel)
                ui_cbx.setChecked(True)
                layout.addWidget(ui_cbx)
                ui_cbx.clicked.connect(self.gallery_filter_selection_changed)
                self.gallery_filter_checkboxes.append(ui_cbx)
                self.gallery_filter_bool[suffix].append(True)
                                           
        ch_filter_content.setLayout(layout)
        
        # delet old container 
        old_container = self.ui_channel_filter.widget()
        if old_container is not None:
            old_container.deleteLater()
        
        self.ui_channel_filter.setWidget(ch_filter_content)
    
    def view_changed(self):
        if self.ui_cb_view.currentIndex() == 1:
            self.viewChangedSignal.emit(3)
        else:
            self.viewChangedSignal.emit(2)
            
    def gallery_filter_selection_changed(self):
        for check_box in self.gallery_filter_checkboxes:
            cb_text = check_box.text()
            suffix = cb_text.split('-')[0]
            channel = cb_text.split('-')[1]
            
            checked = check_box.isChecked()
            ch_idx = self.gallery_filter[suffix].index(channel)
            self.gallery_filter_bool[suffix][ch_idx] = checked
            
        self.filterSelectionChangedSignal.emit()
            
    def is_channel_hidden(self, suffix, channel):
        ch_idx = self.gallery_filter[suffix].index(channel)
        return not self.gallery_filter_bool[suffix][ch_idx]

class DataBrowser(GuiFrame):
    
    def __init__(self, wtype, index, *args, **kwargs):
        super(DataBrowser, self).__init__(wtype, index, *args, **kwargs)
        
        self.initCcUiMembers()
        self.initCcNonUiMembers()
        self.initCcUiLayout()
        self.initCcMenuBar()
        
    def initCcUiMembers(self):
        # 
        self.ui_snap_gallery = ScrollArea()
        self.ui_snap_gallery.resizeSignal.connect(self.resizeGallery)
        self.snap_gallery_container = QtWidgets.QWidget()
        self.ui_snap_gallery.setWidget(self.snap_gallery_container)
        
        # dockWiget filesystem tree
        self.ui_dockWidget_fs_tree = DockWidget()
        self.ui_dockWidget_fs_tree_content = FileSystemTree()
        self.ui_dockWidget_fs_tree_content.selectionChangedSignal.connect(self.fileTreeSelectionChanged)
        
        self.ui_lb_data_path = QtWidgets.QLabel('Data Path:')
        self.ui_le_data_path = QtWidgets.QLineEdit()
        self.ui_pb_change_data_path = QtWidgets.QPushButton('C')
        self.ui_pb_change_data_path.clicked.connect(self.browseDirectry)
        self.ui_pb_change_data_path.setMaximumSize(40,40)
        
        self.ui_lb_data_filter = QtWidgets.QLabel('Format Filter:')
        self.ui_le_data_filter = QtWidgets.QLineEdit()
        self.ui_le_data_filter.editingFinished.connect(self.dataFormatFilterChanged)
        
        self.ui_pb_save_settings = QtWidgets.QPushButton('Save')
        self.ui_pb_save_settings.clicked.connect(self.saveSettings)
        
        # dockWiget GalleryViewManager
        self.ui_dockWidget_gvm = DockWidget()
        self.ui_dockWidget_gvm_content = GalleryViewManager()
        self.ui_dockWidget_gvm_content.viewChangedSignal.connect(self.galleryViewChanged)
        self.ui_dockWidget_gvm_content.filterSelectionChangedSignal.connect(self.galleryFilterSelectionChanged)
        
        #
        self.ui_colorbar = ColorBar()
        self.ui_colorbar.setColorMap('blue1', 1)
        self.ui_colorbar_pixmap = self.ui_colorbar.copyToPixmap()
    
    def initCcUiLayout(self):
        # dockWiget filesystem tree
        ui_horizontalLayout1 = QtWidgets.QHBoxLayout()
        ui_horizontalLayout1.addWidget(self.ui_le_data_path)
        ui_horizontalLayout1.addWidget(self.ui_pb_change_data_path)
        
        ui_verticalLayout1 = QtWidgets.QVBoxLayout()
        ui_verticalLayout1.addWidget(self.ui_lb_data_path)
        ui_verticalLayout1.addLayout(ui_horizontalLayout1)
        ui_verticalLayout1.addWidget(self.ui_lb_data_filter)
        ui_verticalLayout1.addWidget(self.ui_le_data_filter)
        ui_verticalLayout1.addWidget(self.ui_pb_save_settings)
        ui_verticalLayout1.addWidget(self.ui_dockWidget_fs_tree_content)
        
        ui_dock_fs_widgte = QtWidgets.QWidget()
        ui_dock_fs_widgte.setLayout(ui_verticalLayout1)
 
        self.ui_dockWidget_fs_tree.setWidget(ui_dock_fs_widgte)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea , self.ui_dockWidget_fs_tree)
        
        # dockWiget GalleryViewManager
        self.ui_dockWidget_gvm.setWidget(self.ui_dockWidget_gvm_content)
        
        #
        self.tabifyDockWidget(self.ui_dockWideget_var, self.ui_dockWidget_gvm)
        self.tabifyDockWidget(self.ui_dockWidget_gvm, self.ui_dockWidget_fs_tree)
        
        #
        self.ui_horizontalLayout.addWidget(self.ui_snap_gallery)
        
        #
        gallery_layout = QtWidgets.QGridLayout()
        gallery_layout.setContentsMargins(0,0,0,0) # left, top, right, bottom   
        self.snap_gallery_container.setLayout(gallery_layout)
        
        # Set minimum size to current screen size
        screen_geometry = QtWidgets.QApplication.desktop().availableGeometry()
        self.setMinimumSize(screen_geometry.width(), screen_geometry.height()-100)
        #self.setMaximumSize(screen_geometry.width(), screen_geometry.height())
        
    def initCcNonUiMembers(self):
        # Settings
        self.settings = self.loadSettings()
        
        #
        self.snapshots_dir = QtCore.QDir.homePath() + "/angstromPro/snapshots"  # Save snapshots in the user's home directory
        self.snapshots_manager = SnapshotManager(self.snapshots_dir, self.settings)
        
        self.data_format_filter = self.settings['FILTER']['data_format_filter']
        self.ui_le_data_filter.setText(self.data_format_filter)
        
        data_path = self.settings['PATH']['data_path']
        self.ui_le_data_path.setText(data_path)
        self.ui_dockWidget_fs_tree_content.setRootPath(data_path)
        
        #
        self.gallery_contents_per_line = 3
        self.gallery_content_list = []
        self.gallery_content_show_list = []
        self.gallery_filter = {} #dict
        
    def initCcMenuBar(self):
        pass
    
    """ Settings """
    def loadSettings(self):
        return ConfigManager.load_settings_from_file('./ScienceY/config/DataBrowser.txt')
    
    def saveSettings(self):
        ConfigManager.save_settings_to_file('./ScienceY/config/DataBrowser.txt', self.settings)
        
    """   """
    def sendChannelDataToVarList(self, file_path, channel):
        uds_data = self.snapshots_manager.load_channel_data(file_path, channel)
        
        #
        if not uds_data == None:
            self.appendToLocalVarList(uds_data)
    
    def galleryViewChanged(self, content_per_row):
        self.gallery_contents_per_line = content_per_row
        self.updateGallery()
        
    def galleryFilterSelectionChanged(self):
        self.updateGallery()
    
    def browseDirectry(self):
        data_path = self.ui_le_data_path.text()
        
        new_data_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Open File", data_path)
        if not len(new_data_path) == 0:
            self.ui_le_data_path.setText(new_data_path)
            self.settings['PATH']['data_path'] = new_data_path
            
            self.ui_dockWidget_fs_tree_content.setRootPath(new_data_path)
            
    def dataFormatFilterChanged(self):
        text = self.ui_le_data_filter.text()
        self.settings['FILTER']['data_format_filter'] = text
        self.data_format_filter = text
    
    def fileTreeSelectionChanged(self):
        child_folder_files = self.ui_dockWidget_fs_tree_content.selected_child_files
        child_folder_files_lastmodified = self.ui_dockWidget_fs_tree_content.selected_c_f_lastmodified
        
        self.setGallery(child_folder_files, child_folder_files_lastmodified)

    def resizeGallery(self):
        gallery_size = self.ui_snap_gallery.size()
        
        current_container = self.ui_snap_gallery.widget()
        if not current_container == None:
            new_container_width = gallery_size.width() - 30
            current_container.setFixedWidth(new_container_width)
                
            gallery_content_width = int(new_container_width /  self.gallery_contents_per_line)
            gallery_content_height = gallery_content_width
            
            gallery_content_count = len(self.gallery_content_show_list)
            new_container_height = int(np.ceil(gallery_content_count * 1.0 / self.gallery_contents_per_line) * gallery_content_width)
            current_container.setFixedHeight(new_container_height)

            for gallery_content in self.gallery_content_show_list:
                gallery_content.resize(gallery_content_width, gallery_content_height)
                
    def updateGallery(self):
        self.gallery_content_show_list = []
        
        #
        layout = self.snap_gallery_container.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            widget.setParent(None)
        
        shown_contents_count = 0
        for gallery_content in self.gallery_content_list:
            suffix = gallery_content.snapshots_info.src_file_path.split('.')[-1]
            channel = gallery_content.snapshots_info.channel[gallery_content.ch_idx]
            
            if not self.ui_dockWidget_gvm_content.is_channel_hidden(suffix, channel):
                row = shown_contents_count // self.gallery_contents_per_line  # Determine the row (2 rows, 0 and 1)
                col = shown_contents_count % self.gallery_contents_per_line   # Determine the column (3 columns, 0, 1, 2)     
                shown_contents_count += 1
                self.gallery_content_show_list.append(gallery_content)
                layout.addWidget(gallery_content, row, col)
        #
        self.resizeGallery()        

    def setGallery(self, src_files_path, src_files_lastmodified):        
        gallery_content_counts = 0
        self.gallery_content_list = []
        self.gallery_filter = {}
        
        for index, file_path in enumerate(src_files_path):
            # file suffix filter
            suffix = file_path.split('.')[-1]          
            if suffix not in self.data_format_filter:
                continue
            
            metadata_file_path= self.getSnapshotsInfo(file_path, src_files_lastmodified[index])
            snapshots_info = self.snapshots_manager.load_metadata_file(metadata_file_path)
            for ch_idx, channel in enumerate(snapshots_info.channel):
                gallery_content_counts += 1
                gallery_content = GalleryContentWidget(self.snapshots_manager, snapshots_info, ch_idx, self.ui_colorbar_pixmap)          
                gallery_content.sendChannelDataSignal.connect(self.sendChannelDataToVarList)
                self.gallery_content_list.append(gallery_content)
        
        # get all suffixes and its channels
        for gallery_content in self.gallery_content_list:
            suffix = gallery_content.snapshots_info.src_file_path.split('.')[-1]
            if not suffix in self.gallery_filter:
                self.gallery_filter[suffix] = []
            
            channel = gallery_content.snapshots_info.channel[gallery_content.ch_idx]
            ch_list =self.gallery_filter.get(suffix)
            if not channel in ch_list:
                self.gallery_filter[suffix].append(channel)

        self.ui_dockWidget_gvm_content.set_gallery_filter(self.gallery_filter)         
        
        #
        self.updateGallery()
       
    def getSnapshotsInfo(self,src_file_path, src_file_lastmodified):
        metadata_file_path = self.snapshots_manager.get_snapshots_info(src_file_path, src_file_lastmodified)
         
        if not metadata_file_path:
            self.snapshots_manager.generate_snapshots(src_file_path, src_file_lastmodified)
            
            # get updated png name
            metadata_file_path = self.snapshots_manager.get_snapshots_info(src_file_path, src_file_lastmodified)
            
        return metadata_file_path
    
    
        """
        #
        gallery_content_list[0].setFixedHeight(386)
        gallery_content_list[0].setFixedWidth(386)
        #gallery_content_list[0].setAttribute(QtCore.Qt.WA_TranslucentBackground)
        gallery_content_list[0].setStyleSheet("QWidget { background-color: #FFFFFF; }")
        pixmap = QtGui.QPixmap(gallery_content_list[0].size())
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        gallery_content_list[0].render(painter)
        painter.end()
        
        QtWidgets.QApplication.clipboard().setPixmap(pixmap)
        """
