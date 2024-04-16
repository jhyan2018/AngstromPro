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
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal
import matplotlib.pyplot as plt

"""
User Modules
"""
from .ColorBar import ColorBar
"""
Modules Definition
"""

class PreferenceIUD2or3D(QtWidgets.QMainWindow):
    save_settings = pyqtSignal()
    
    def __init__(self,title='', *args, **kwargs):
        super(PreferenceIUD2or3D, self).__init__(*args, **kwargs)        
        self.setWindowTitle(title)
        self.initUiMembers()
        self.initUiLayout()
        
    def setSettings(self, settings):
        self.settings = settings
        
        # palette
        ccmap = self.settings['COLORMAP']['cmap_palette_list'].split(',')
        self.ui_lw_chosen_cmp_list.addItems(ccmap)

    def initUiMembers(self):
        self.resize(1000,600)
        # Main widget and layout
        self.ui_centralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.ui_centralWidget)
        self.ui_mainLayout = QtWidgets.QHBoxLayout(self.ui_centralWidget)

        # Side panel for options
        self.ui_optionList = QtWidgets.QListWidget()
        self.ui_optionList.insertItem(0, "ColorMap")
        self.ui_optionList.insertItem(1, "Option 2")
        self.ui_optionList.insertItem(2, "Option 3")
        self.ui_optionList.currentItemChanged.connect(self.changePage)
        self.ui_mainLayout.addWidget(self.ui_optionList, alignment=Qt.AlignLeft)

        # Stack of widgets for different pages
        self.ui_pages = QtWidgets.QStackedWidget()
        self.ui_setupPageColorMap()
        self.ui_setupPage2()
        self.ui_setupPage3()
        self.ui_pages.addWidget(self.ui_page_colormap)
        self.ui_pages.addWidget(self.ui_page2)
        self.ui_pages.addWidget(self.ui_page3)
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
        self.ui_pb_save_chosen_list = QtWidgets.QPushButton('Save')
        self.ui_pb_save_chosen_list.clicked.connect(self.saveChosenList)
        self.ui_colorbar = ColorBar()
        
        self.ui_lw_cmp_list.itemSelectionChanged.connect(self.colormapListActivatedItemChanged)
        
    def ui_setupPage2(self):
        self.ui_page2 = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        button = QtWidgets.QPushButton("Click me")
        layout.addWidget(button)
        self.ui_page2.setLayout(layout)

    def ui_setupPage3(self):
        self.ui_page3 = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        slider = QtWidgets.QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(50)
        layout.addWidget(slider)
        self.ui_page3.setLayout(layout)
        
    def initUiLayout(self):
        #Page ColorMap
        v_layout1 = QtWidgets.QVBoxLayout()
        v_layout1.addWidget(self.ui_cb_cmp_type)
        v_layout1.addWidget(self.ui_lw_cmp_list)
        v_layout2 = QtWidgets.QVBoxLayout()
        v_layout2.addWidget(self.ui_pb_add_to_cmp_chosen_list)
        v_layout2.addWidget(self.ui_pb_moveup_item_in_chosen_list)
        v_layout2.addWidget(self.ui_pb_movedown_item_in_chosen_list)
        v_layout2.addWidget(self.ui_pb_remove_from_cmp_chosen_list)
        v_layout2.addWidget(self.ui_pb_save_chosen_list)
        v_layout3 = QtWidgets.QVBoxLayout()
        v_layout3.addWidget(self.ui_lb_chosen_cmp_list)
        v_layout3.addWidget(self.ui_lw_chosen_cmp_list)        
        h_layout1 = QtWidgets.QHBoxLayout()
        h_layout1.addLayout(v_layout1)
        h_layout1.addWidget(self.ui_colorbar)
        h_layout1.addLayout(v_layout2)
        h_layout1.addLayout(v_layout3)
        self.ui_page_colormap.setLayout(h_layout1)
        
        #
        
    """ @SLOT"""    
    def saveSettings(self):
        self.save_settings.emit()
        
    def changePage(self, current, previous):
        if current:
            self.ui_pages.setCurrentIndex(self.ui_optionList.row(current))
    
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
        self.ui_colorbar.setColorMap(cmap, ctype)
    
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
    
    def saveChosenList(self):
        chosen_cmap_list = []
        for index in range(self.ui_lw_chosen_cmp_list.count()):
            chosen_cmap_list.append(self.ui_lw_chosen_cmp_list.item(index).text())
        
        separator = ','
        self.settings['COLORMAP']['cmap_palette_list'] = separator.join(chosen_cmap_list)
        
        self.save_settings.emit()