# -*- coding: utf-8 -*-
"""
Created on Sat May  4 11:41:36 2024

@author: jiahaoYan
"""

"""
System modules
"""

"""
Third-party Modules
"""
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QFileInfo
"""
User Modules
"""
from .GuiFrame import GuiFrame
from .FileSystemTree import FileSystemTree
from .SnapshotManager import SnapshotManager
from .ConfigManager import ConfigManager

""" *************************************** """
""" DO NOT MODIFY THE REGION UNTIL INDICATED"""
""" *************************************** """

class DataBrowser(GuiFrame):
    
    def __init__(self, wtype, index, *args, **kwargs):
        super(DataBrowser, self).__init__(wtype, index, *args, **kwargs)        
        
        self.initCcUiMembers()
        self.initCcUiLayout()
        self.initCcNonUiMembers()
        self.initCcMenuBar()
        
    def initCcUiMembers(self):
        # 
        self.ui_snap_gallery = QtWidgets.QScrollArea()
        
        # dockWiget filesystem tree
        self.ui_dockWidget_fs_tree = QtWidgets.QDockWidget()
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

        #
        self.ui_dockWideget_var.close()
    
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
           
        self.tabifyDockWidget(self.ui_dockWideget_var ,self.ui_dockWidget_fs_tree)
        
        #
        self.ui_horizontalLayout.addWidget(self.ui_snap_gallery)
        self.ui_snap_gallery.setWidgetResizable(True)
        
    def initCcNonUiMembers(self):
        # Settings
        self.settings = self.loadSettings()
        
        #
        self.snapshots_dir = QtCore.QDir.homePath() + "/ScienceY/snapshots"  # Save snapshots in the user's home directory
        self.snapshots_manager = SnapshotManager(self.snapshots_dir)
        
        self.data_format_filter = self.settings['FILTER']['data_format_filter']
        self.ui_le_data_filter.setText(self.data_format_filter)
        
        data_path = self.settings['PATH']['data_path']
        self.ui_le_data_path.setText(data_path)
        self.ui_dockWidget_fs_tree_content.setRootPath(data_path)
        
    def initCcMenuBar(self):
        pass
    
    """ Settings """
    def loadSettings(self):
        return ConfigManager.load_settings_from_file('./ScienceY/config/DataBrowser.txt')
    
    def saveSettings(self):
        ConfigManager.save_settings_to_file('./ScienceY/config/DataBrowser.txt', self.settings)
    
    """   """
    def browseDirectry(self):
        data_path = self.ui_le_data_path.text()
        
        new_data_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Open File", data_path)
        if new_data_path is not None:
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
        
    def setGallery(self, src_files_path, src_files_lastmodified):
        snap_gallery_container = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout()
        
        gallery_content_counts = 0
        gallery_content_list = []
        
        for index, file_path in enumerate(src_files_path):
            # file suffix filter
            suffix = file_path.split('.')[-1]          
            if suffix not in self.data_format_filter:
                continue
            
            png_path_list, channel_list = self.getSnapshotsInfo(file_path, src_files_lastmodified[index])
            for path in png_path_list:
                file_info = QFileInfo(path)
                if file_info.isDir():
                    png_path = path + '/l0'
                else:
                    png_path = path
                gallery_content_counts += 1
                
                """ should change to other widget """
                label = QtWidgets.QLabel()              
                pixmap = QtGui.QPixmap(png_path)
                label.setPixmap(pixmap)
                gallery_content_list.append(label)                
                #channel_list               
            
        for index, gallery_content in enumerate(gallery_content_list):
            row = index // 3  # Determine the row (2 rows, 0 and 1)
            col = index % 3   # Determine the column (3 columns, 0, 1, 2)     
            
            layout.addWidget(gallery_content, row, col)
            
        snap_gallery_container.setLayout(layout)
        
        # delet old gallary container 
        old_container = self.ui_snap_gallery.widget()
        if old_container is not None:
            old_container.deleteLater()
            
        #
        self.ui_snap_gallery.setWidget(snap_gallery_container)
        
    def getSnapshotsInfo(self,src_file_path, src_file_lastmodified):
        png_path_list, lastmodified, channel_list = self.snapshots_manager.get_snapshots_info(src_file_path)
        
        if not png_path_list or not src_file_lastmodified == lastmodified:
            pixmap_list, channel_list, channel_layer_list = self.snapshots_manager.generate_snapshots(src_file_path)
            self.snapshots_manager.save_snapshots(src_file_path, src_file_lastmodified, pixmap_list, channel_list, channel_layer_list)
            
            # get updated png name
            png_path_list, lastmodified, channel_list = self.snapshots_manager.get_snapshots_info(src_file_path)
            
        return png_path_list, channel_list
