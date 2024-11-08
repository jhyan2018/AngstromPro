# -*- coding: utf-8 -*-
"""
Created on Tue Oct 15 11:44:11 2024

@author: jiahaoYan
"""


"""
System modules
"""
from collections import defaultdict

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
class PlotObjManager:
    def __init__(self, fig_obj=None):
        self.figure_obj = fig_obj
        self.axes_and_data = defaultdict(lambda:{
            'axis_obj': None,             # Stores the Matplotlib Axes object
            'curves': defaultdict(lambda:{
                'curve_obj':[]
            })
        })
        
    def set_figure(self, fig_obj=None):
        self.figure_obj = fig_obj
        
    def add_axis(self, axis_obj, axis_name='Axis_1_1'):
        self.axes_and_data[axis_name]['axis_obj'] = axis_obj
        
    def remove_axis(self, axis_name='Axis_1_1'):
        pass
        
    def add_curve_to_axis(self, udata_name, curve_obj, axis_name='Axis_1_1'):
        self.axes_and_data[axis_name]['curves'][udata_name]['curve_obj'].append(curve_obj)
    
    def remove_curve_from_axis(self,udata_name, curve_obj, axis_name='Axis_1_1'):
        pass
    
    def get_figure(self):
        return self.figure_obj
        
    def get_aixs(self, axis_name='Axis_1_1'):
        return self.axes_and_data[axis_name]['axis_obj']
    
    def get_curve(self, udata_name, curve_idx, axis_name='Axis_1_1'):
        return self.axes_and_data[axis_name]['curves'][udata_name]['curve_obj'][curve_idx]

class PlotConfigKey:
    # Figure
    
    # Axis
    X_LABEL = 'xlabel'
    Y_LABEL = 'ylabel'
    # Line
    LINE_WIDTH = 'line_width'
    
    #FONT
    FONT_SIZE = 'font_size'
 
class PlotConfig():
    def __init__(self, config_base=None):
        # Load the base configuration templates
        self.load_config_base(config_base)
        
        # Initialize figure configuration from the base config
        self.config_figure = self.config_figure_base.copy()
        self.config_axis = self.config_axis_base.copy()
        
        # Initialize empty lists for line configurations
        
        self.config_line_list = []
        
    def load_config_base(self, config_base):
        """Load the base configurations for figure, axis, and line."""
        # Base configuration for the figure
        self.config_figure_base={}
        
        # Base configuration for axes
        self.config_axis_base={}
        
        # Base configuration for lines
        self.config_line_base={'linestyle':'-',
                               'linewidth':2}
        
        if config_base:
            self.update_config_base(config_base)
        
    """ Themes """
    def update_config_base(self, config):
        #self.config_figure_base.update(config.get('figure', {}))
        #self.config_axis_base.update(config.get('axis', {}))
        #self.config_line_base.update(config.get('line', {}))
        pass
    def load_config_base_from_file(self, path):
        pass
    def save_config_base_to_file(self, path):
        pass
    
    """ """   
    def add_config_line(self, new_config=None):
        """
        Add a line configuration to the line list.
        If new_config is provided, it updates the base configuration.
        """
        line_config = self.config_line_base.copy()
        if new_config:
            line_config.update(new_config)
        self.config_line_list.append(line_config)
    
        
    """ Update configurations"""
    def update_figure_config(self, config):
        self.config_figure.update(config)
    
    def update_axis_config(self, config):
        self.config_axis.update(config)
    
    def update_line_config(self, line_idx, config):
        self.config_line_list[line_idx].update(config)


class PlotConfigHandler:
    def __init__(self):
        pass
    
    """ Apply configurations"""
    def set_obj_key_value(self, obj, key, value):
        method_name = f'handle_{key}' # Build method name dynamically
        handler = getattr(self, method_name, None)
        if handler:
            handler(obj, value) # call the method if it exists
    
    def apply_figure_config(self, obj_fig, config_fig):       
        for key, value in config_fig.items():
            self.set_obj_key_value(obj_fig, key, value)

    def apply_axis_config(self, obj_axis, config_axis):
        for key, value in config_axis.items():
            self.set_obj_key_value(obj_axis, key, value)

    def apply_line_config(self, obj_line, config_line):
        for key, value in config_line.items():
            self.set_obj_key_value(obj_line, key, value)

    """ Dynamic Functions """
    # Figure
    def handle_figsize(self, fig, value):
        fig.set_size_inches(value)
        
    def handle_dpi(self, fig, value):
        fig.set_dpi(value)
        
    def handle_facecolor(self, fig, value):
        fig.set_facecolor(value)

    def handle_suptitle(self, fig, value):
        fig.suptitle(value)
        
    # Axis
    def handle_xlabel(self, ax, value):
        ax.set_xlabel(value)
    
    def handle_ylabel(self, ax, value):
        ax.set_ylabel(value)

    def handle_title(self, ax, value):
        ax.set_title(value)
        
    def handle_xlim(self, ax, value):
        ax.set_xlim(value)

    def handle_ylim(self, ax, value):
        ax.set_ylim(value)

    def handle_xticks(self, ax, value):
        ax.set_xticks(value)

    def handle_yticks(self, ax, value):
        ax.set_yticks(value)   
    
    # position
    def handle_position(self, ax, value):
        ax.set_position(value)
    
    def handle_title_position(self, ax, value):
        ax.title.set_position(value)

    def handle_label_position(self, ax, axis, value):
        if axis == 'x':
            ax.xaxis.set_label_position(value)
        elif axis == 'y':
            ax.yaxis.set_label_position(value)
            
    # --- Grid ---
    def handle_grid(self, ax, value):
        ax.grid(value)
        
    def handle_grid_color(self, ax, value):
        ax.grid(True, color=value)

    def handle_grid_linestyle(self, ax, value):
        ax.grid(True, linestyle=value)

    def handle_grid_linewidth(self, ax, value):
        ax.grid(True, linewidth=value)
     
    # --- Legend ---
    def handle_legend(self, ax, **kwargs):
        ax.legend(**kwargs)

    def handle_legend_loc(self, ax, value):
        legend = ax.get_legend()
        if legend:
            legend.set_loc(value)

    def handle_legend_fontsize(self, ax, value):
        legend = ax.get_legend()
        if legend:
            legend.set_fontsize(value)

    def handle_legend_frameon(self, ax, value):
        legend = ax.get_legend()
        if legend:
            legend.set_frame_on(value)
            
    # Ticks
    def handle_tick_params(self, ax, **kwargs):
        ax.tick_params(**kwargs)

    def handle_xtick_rotation(self, ax, value):
        for label in ax.get_xticklabels():
            label.set_rotation(value)

    def handle_ytick_rotation(self, ax, value):
        for label in ax.get_yticklabels():
            label.set_rotation(value)

    def handle_tick_labelsize(self, ax, value):
        ax.tick_params(labelsize=value)
        
    # Spine
    def handle_spine_visible(self, ax, spine, value):
        ax.spines[spine].set_visible(value)

    def handle_spine_color(self, ax, spine, value):
        ax.spines[spine].set_color(value)

    def handle_spine_linewidth(self, ax, spine, value):
        ax.spines[spine].set_linewidth(value)
     
    # Font
    def handle_font(self, ax, prop, value):
        for label in [ax.title, ax.xaxis.label, ax.yaxis.label]:
            label.set_fontsize(value)

    def handle_title_fontsize(self, ax, value):
        ax.title.set_fontsize(value)

    def handle_label_fontsize(self, ax, value):
        ax.xaxis.label.set_fontsize(value)
        ax.yaxis.label.set_fontsize(value)

    def handle_tick_fontsize(self, ax, value):
        ax.tick_params(labelsize=value)
        
    # Color bar
    def handle_colorbar(self, colorbar, **kwargs):
        colorbar.set_ticks(kwargs.get('ticks', []))
        colorbar.set_ticklabels(kwargs.get('ticklabels', []))
        
    # Line
    def handle_linecolor(self, line, value):
        line.set_color(value)
    
    def handle_linestyle(self, line, value):
        line.set_linestyle(value)
    
    def handle_linewidth(self, line, value):
        line.set_linewidth(value)
    
    def handle_marker(self, line, value):
        line.set_marker(value)

    def handle_label(self, line, value):
        line.set_label(value)

    def handle_alpha(self, line, value):
        line.set_alpha(value)

    def handle_zorder(self, line, value):
        line.set_zorder(value)
    

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
        self.obj_fig = None
        self.obj_axis = None
        self.obj_line = None
    
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
        self.linewidth_spinbox.valueChanged.connect(self.config_linewidth_changed)
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

    """ @SLOTS of UI Widgets"""
    def config_linewidth_changed(self):

        if self.obj_line:
            line_width = self.linewidth_spinbox.value()
            self.obj_line.set_linewidth(line_width)          
            self.obj_fig.canvas.draw()
            
        # emit signal to plg_obj_mgr to update config in uds_data
    
    """ Regular Functions """
    def set_obj_figure(self, obj_fig):
        self.obj_fig = obj_fig
        
        # get all present fig configs
        
    def set_obj_axis(self, obj_axis):
        self.obj_axis = obj_axis
        
        # get all present axis configs
        
    def set_obj_curve(self, obj_curve):
        self.obj_line = obj_curve
        
        # get all present curve config