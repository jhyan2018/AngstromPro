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
import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui

"""
User Modules
"""
from .GuiFrame import GuiFrame
from .FileSystemTree import FileSystemTree
from .SnapshotManager import SnapshotManager

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
        
        # dockWiget Plot1D
        self.ui_dockWidget_fs_tree = QtWidgets.QDockWidget()
        self.ui_dockWidget_fs_tree_content = FileSystemTree('E:/gdrive/Python/examples/')
        self.ui_dockWidget_fs_tree_content.selectionChangedSignal.connect(self.fileTreeSelectionChanged)

        self.ui_dockWidget_fs_tree.setWidget(self.ui_dockWidget_fs_tree_content)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea , self.ui_dockWidget_fs_tree)
        
        #
        self.tabifyDockWidget(self.ui_dockWideget_var ,self.ui_dockWidget_fs_tree)

        #
        self.ui_dockWideget_var.close()
    
    def initCcUiLayout(self):
        self.ui_horizontalLayout.addWidget(self.ui_snap_gallery)
        #
        self.ui_snap_gallery.setWidgetResizable(True)
        
    def initCcNonUiMembers(self):
        self.snapshots_dir = QtCore.QDir.homePath() + "/ScienceY/snapshots"  # Save snapshots in the user's home directory
        self.snapshots_manager = SnapshotManager(self.snapshots_dir)
        
    def initCcMenuBar(self):
        pass
    
    def fileTreeSelectionChanged(self):
        child_folder_files = self.ui_dockWidget_fs_tree_content.selected_child_files
        
        self.setGallary(child_folder_files)
        
    def setGallary(self, data_files):
        #print(data_files)
        
        snap_gallery_container = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout()
        
        for index, img_path in enumerate(data_files):
            row = index // 3  # Determine the row (2 rows, 0 and 1)
            col = index % 3   # Determine the column (3 columns, 0, 1, 2)
            
            label = QtWidgets.QLabel()
            pixmap = QtGui.QPixmap(img_path)
            label.setPixmap(pixmap)
            layout.addWidget(label, row, col)
            
        snap_gallery_container.setLayout(layout)
        
        # delet old gallary container 
        old_container = self.ui_snap_gallery.widget()
        if old_container is not None:
            old_container.deleteLater()
        
        self.ui_snap_gallery.setWidget(snap_gallery_container)
