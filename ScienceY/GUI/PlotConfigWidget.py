# -*- coding: utf-8 -*-
"""
Created on Tue Oct 15 11:44:11 2024

@author: jiahaoYan
"""


"""
System modules
"""

"""
Third-party Modules
"""
import numpy as np
import matplotlib.pyplot as plt
from PyQt5 import QtCore, QtWidgets, QtGui
"""
User Modules
"""


""" *************************************** """
""" DO NOT MODIFY THE REGION UNTIL INDICATED"""
""" *************************************** """

class PlotConfigWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(PlotConfigWidget, self).__init__( *args, **kwargs)
        
        self.initNonUiMembers()        
        self.initUiMembers()
        self.initUiLayout()
        
    def initUiMembers(self):
        # Create QToolBox for collapsible sections
        self.ui_toolbox = QtWidgets.QToolBox()
        self.ui_toolbox.addItem(self.create_figure_config_group(), "Figure Configuration")
        self.ui_toolbox.addItem(self.create_axes_config_group(), "Axis Configuration")
        self.ui_toolbox.addItem(self.create_line_config_group(), "Line Configuration")
        self.ui_toolbox.addItem(self.create_tick_config_group(),'Tick Configuration')
        self.ui_toolbox.addItem(self.create_legend_config_group(),'Legend Configuration')
        self.ui_toolbox.addItem(self.create_grid_config_group(),'Grid Configuration')
        self.ui_toolbox.addItem(self.create_spine_config_group(),'Spine Configuration')
        self.ui_toolbox.addItem(self.create_annotation_config_group(),'Annotation Configuration')
    
    def initNonUiMembers(self):
        pass
    
    def initUiLayout(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.ui_toolbox)
        self.setLayout(main_layout)
    
    """ Create Configure Group"""
    def create_figure_config_group(self):
        """Create a QWidget for figure-level configurations."""
        group_widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(group_widget)
        
        # Figure size
        self.figure_width = QtWidgets.QSpinBox()
        self.figure_width.setValue(10)
        self.figure_height = QtWidgets.QSpinBox()
        self.figure_height.setValue(10)
        layout.addRow(QtWidgets.QLabel("Width:"),self.figure_width)
        layout.addRow(QtWidgets.QLabel("Height:"),self.figure_height)
        
        # DPI setting
        self.dpi_spinbox = QtWidgets.QSpinBox()
        self.dpi_spinbox.setRange(50, 300)
        self.dpi_spinbox.setValue(100)
        layout.addRow(QtWidgets.QLabel("DPI:"), self.dpi_spinbox)
        
        # Figure title setting
        self.fig_title_input = QtWidgets.QLineEdit()
        layout.addRow(QtWidgets.QLabel("Figure Title:"), self.fig_title_input)
        
        # Face color setting
        self.facecolor_button = QtWidgets.QPushButton("C")
        self.facecolor_button.clicked.connect(self.choose_face_color)
        self.facecolor_value = QtWidgets.QLineEdit("white")  # Display the selected color
        layout_facecolor = QtWidgets.QHBoxLayout()
        layout_facecolor.addWidget(self.facecolor_value)
        layout_facecolor.addWidget(self.facecolor_button)       
        layout.addRow(QtWidgets.QLabel("Face Color:"), layout_facecolor)
        
        # Edge color setting
        self.edgecolor_button = QtWidgets.QPushButton("C")
        self.edgecolor_button.clicked.connect(self.choose_edge_color)
        self.edgecolor_value = QtWidgets.QLineEdit("black")  # Display the selected color
        layout_edgecolor = QtWidgets.QHBoxLayout()
        layout_edgecolor.addWidget(self.edgecolor_value)
        layout_edgecolor.addWidget(self.edgecolor_button)
        layout.addRow(QtWidgets.QLabel("Edge Color:"), layout_edgecolor)
        
        # Transparency
        self.figure_transparency = QtWidgets.QSpinBox()
        self.figure_transparency.setValue(10)
        layout.addRow(QtWidgets.QLabel("Transparency:"),self.figure_transparency)

        # Padding
        self.figure_padding = QtWidgets.QSpinBox()
        self.figure_padding.setValue(10)
        layout.addRow(QtWidgets.QLabel("Padding:"),self.figure_padding)
        
        # Frame
        self.figure_frame = QtWidgets.QCheckBox()
        layout.addRow(QtWidgets.QLabel("Frame:"),self.figure_frame)
        
        return group_widget

    def create_axes_config_group(self):
        """Create a QWidget for axes configurations."""
        group_widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(group_widget)

        # Axis titles
        self.xlabel_input = QtWidgets.QLineEdit()
        self.ylabel_input = QtWidgets.QLineEdit()
        layout.addRow(QtWidgets.QLabel("X-axis Label:"), self.xlabel_input)
        layout.addRow(QtWidgets.QLabel("Y-axis Label:"), self.ylabel_input)

        # Axis limits
        self.xlim_min_input = QtWidgets.QLineEdit()
        self.xlim_max_input = QtWidgets.QLineEdit()
        self.ylim_min_input = QtWidgets.QLineEdit()
        self.ylim_max_input = QtWidgets.QLineEdit()
        layout.addRow(QtWidgets.QLabel("X-axis Min:"), self.xlim_min_input)
        layout.addRow(QtWidgets.QLabel("X-axis Max:"), self.xlim_max_input)
        layout.addRow(QtWidgets.QLabel("Y-axis Min:"), self.ylim_min_input)
        layout.addRow(QtWidgets.QLabel("Y-axis Max:"), self.ylim_max_input)

        # Axes title
        self.axes_title_input = QtWidgets.QLineEdit()
        layout.addRow(QtWidgets.QLabel("Axes Title:"), self.axes_title_input)

        # Aspect ratio
        self.aspect_ratio = QtWidgets.QLineEdit()
        layout.addRow(QtWidgets.QLabel("Aspect ratio:"), self.aspect_ratio)
        
        # Scale
        self.log_scale = QtWidgets.QComboBox()
        self.log_scale.addItems(['Linear','Log'])
        layout.addRow(QtWidgets.QLabel("Scale:"), self.log_scale)
        
        # Axis position

        return group_widget

    def create_line_config_group(self):
        """Create a QWidget for line configuration."""
        group_widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(group_widget)

        # Line width setting
        self.linewidth_spinbox = QtWidgets.QSpinBox()
        self.linewidth_spinbox.setRange(1, 10)
        self.linewidth_spinbox.setValue(2)
        layout.addRow(QtWidgets.QLabel("Line Width:"), self.linewidth_spinbox)

        # Line style setting
        self.linestyle_combobox = QtWidgets.QComboBox()
        self.linestyle_combobox.addItems(["-", "--", "-.", ":"])
        layout.addRow(QtWidgets.QLabel("Line Style:"), self.linestyle_combobox)

        # Line color setting
        self.linecolor_button = QtWidgets.QPushButton("Choose Line Color")
        self.linecolor_button.clicked.connect(self.choose_line_color)
        self.linecolor_label = QtWidgets.QLabel("blue")  # Display the selected color
        layout.addRow(QtWidgets.QLabel("Line Color:"), self.linecolor_button)
        layout.addRow(QtWidgets.QLabel("Selected:"), self.linecolor_label)

        # Marker style setting
        self.marker_combobox = QtWidgets.QComboBox()
        self.marker_combobox.addItems(["o", "s", "D", "^", "v", "None"])
        layout.addRow(QtWidgets.QLabel("Marker Style:"), self.marker_combobox)

        # Marker size setting
        self.marker_size_spinbox = QtWidgets.QSpinBox()
        self.marker_size_spinbox.setRange(1, 20)
        self.marker_size_spinbox.setValue(6)
        layout.addRow(QtWidgets.QLabel("Marker Size:"), self.marker_size_spinbox)

        return group_widget
    
    def create_tick_config_group(self):
        group_widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(group_widget)
        
        # Axis ticks
        self.xticks_input = QtWidgets.QLineEdit()
        self.yticks_input = QtWidgets.QLineEdit()
        layout.addRow(QtWidgets.QLabel("X-axis Ticks (comma-separated):"), self.xticks_input)
        layout.addRow(QtWidgets.QLabel("Y-axis Ticks (comma-separated):"), self.yticks_input)

        return group_widget
    
    def create_legend_config_group(self):
        group_widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(group_widget)
        
        return group_widget
    
    def create_grid_config_group(self):
        group_widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(group_widget)
        
        # Grid option
        self.grid_checkbox = QtWidgets.QCheckBox("Show Grid")
        layout.addRow(self.grid_checkbox)
        
        return group_widget
    
    def create_spine_config_group(self):
        group_widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(group_widget)
        
        return group_widget
    
    def create_annotation_config_group(self):
        group_widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(group_widget)
        
        return group_widget
    
    def choose_face_color(self):
        """Open a color dialog to choose the figure face color."""
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.facecolor_value.setText(color.name())  # Update the label text

    def choose_edge_color(self):
        """Open a color dialog to choose the figure edge color."""
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.edgecolor_label.setText(color.name())  # Update the label text

    def choose_line_color(self):
        """Open a color dialog to choose the line color."""
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.linecolor_label.setText(color.name())  # Update the label text
