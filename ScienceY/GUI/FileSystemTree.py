# -*- coding: utf-8 -*-
"""
Created on Sat May  4 16:45:18 2024

@author: jiahaoYan
"""

from PyQt5.QtWidgets import QLabel, QTreeView, QFileSystemModel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QDir, QFileInfo, pyqtSignal

class FileSystemTree(QWidget):
    selectionChangedSignal = pyqtSignal()
    def __init__(self, root_path):
        super().__init__()

        layout = QVBoxLayout()

        # Create the file system model
        self.model = QFileSystemModel()
        #self.model.setRootPath(root_path)

        # Create the tree view
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        
        #
        self.selected_child_files = []
        
        # Create a label to display the last modified time
        self.label = QLabel("Select a file or folder to view its last modified time")

        # Set up the layout
        layout.addWidget(self.tree)
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        #
        self.setRootPath(root_path)
        
        # Connect selection change signal
        self.tree.selectionModel().selectionChanged.connect(self.fileTreeSelectionChanged)

        
    def setRootPath(self, root_path):
        self.model.setRootPath(root_path)
        root_index = self.model.index(root_path)
        self.tree.setRootIndex(root_index)
    
    def get_all_files_and_folders(self, parent_folder): 
        collected_items = []
    
        # Initialize a QDir object with the provided parent folder
        directory = QDir(parent_folder)
        directory.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)  # Ignore `.` and `..`
    
        # Retrieve all entries in the current directory
        entry_info_list = directory.entryInfoList()
    
        # Iterate through each entry to collect its path
        for entry_info in entry_info_list:
            path = entry_info.absoluteFilePath()  
            
            # If it's a directory, recurse into it
            if entry_info.isDir():
                collected_items.extend(self.get_all_files_and_folders(path))
            else:
                collected_items.append(path) # only return files
                    
        return collected_items
    
    def fileTreeSelectionChanged(self):
        index = self.tree.selectionModel().currentIndex()
        path = self.model.filePath(index)
        
        # check if it's file, then return parent folder path
        file_info = QFileInfo(path)        
        if not file_info.isDir():
            path = file_info.absolutePath()

        #   
        self.selected_child_files = self.get_all_files_and_folders(path)
        self.selectionChangedSignal.emit()
    
    def display_last_modified_time(self):
        # Get the current selection from the selection model
        pass

        """
        indexes = self.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            file_info = self.model.fileInfo(index)
            last_modified = file_info.lastModified().toString(Qt.ISODate)
            self.label.setText(f"{last_modified}")
        """