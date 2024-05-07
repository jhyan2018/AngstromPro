# -*- coding: utf-8 -*-
"""
Created on Sat May  4 16:45:18 2024

@author: jiahaoYan
"""

from PyQt5.QtWidgets import QTreeView, QFileSystemModel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QDir, QFileInfo, pyqtSignal

class FileSystemTree(QWidget):
    selectionChangedSignal = pyqtSignal()
    def __init__(self, root_path):
        super().__init__()

        layout = QVBoxLayout()

        # Create the file system model
        self.model = QFileSystemModel()

        # Create the tree view
        self.tree = QTreeView()
        self.tree.setModel(self.model)
       
        self.setRootPath(root_path)
        
        # Connect selection change signal
        self.tree.selectionModel().selectionChanged.connect(self.fileTreeSelectionChanged)
        
        # Set up the layout
        layout.addWidget(self.tree)
        self.setLayout(layout)
        
        #
        self.selected_child_files = []
        self.selected_c_f_lastmodified = []
        
    def setRootPath(self, root_path):
        self.model.setRootPath(root_path)
        root_index = self.model.index(root_path)
        self.tree.setRootIndex(root_index)
    
    def get_all_files_and_folders(self, parent_folder): 
        all_files_path = []
        all_files_lastmodified = []
    
        # Initialize a QDir object with the provided parent folder
        directory = QDir(parent_folder)
        directory.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)  # Ignore `.` and `..`
    
        # Retrieve all entries in the current directory
        entry_info_list = directory.entryInfoList()
    
        # Iterate through each entry to collect its path
        for entry_info in entry_info_list:
            path = entry_info.absoluteFilePath()  
            lastmodified = entry_info.lastModified().toString(Qt.ISODate)
            
            # If it's a directory, recurse into it
            if entry_info.isDir():
                paths, lms = self.get_all_files_and_folders(path)
                all_files_path.extend(paths)
                all_files_lastmodified.extend(lms)
            else:
                all_files_path.append(path) # only return files
                all_files_lastmodified.append(lastmodified)
                    
        return all_files_path, all_files_lastmodified
    
    def fileTreeSelectionChanged(self):
        index = self.tree.selectionModel().currentIndex()
        path = self.model.filePath(index)
        
        # check if it's file, then return parent folder path
        file_info = QFileInfo(path)        
        if not file_info.isDir():
            path = file_info.absolutePath()

        #   
        self.selected_child_files, self.selected_c_f_lastmodified = self.get_all_files_and_folders(path)
        self.selectionChangedSignal.emit()