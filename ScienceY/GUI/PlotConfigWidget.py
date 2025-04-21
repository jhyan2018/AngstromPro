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
from PyQt5 import QtWidgets
"""
User Modules
"""
from .customizedWidgets.SimplifiedNumberLineEditor import SimplifiedNumberLineEditor

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
    
    def remove_all_curves_from_axis(self, axis_name='Axis_1_1'):
        self.axes_and_data[axis_name]['curves'].clear()
    
    def get_figure(self):
        return self.figure_obj
        
    def get_aixs(self, axis_name='Axis_1_1'):
        return self.axes_and_data[axis_name]['axis_obj']
    
    def get_curve(self, udata_name, curve_idx, axis_name='Axis_1_1'):
        return self.axes_and_data[axis_name]['curves'][udata_name]['curve_obj'][curve_idx]

class PlotConfigKey:
    # Figure
    FIGURE_SIZE = 'figsize'
    DPI = 'dpi'
    FIGURE_TITLE = 'suptitle'
    FIGURE_FACECOLOR = 'figfacecolor'
    FIGURE_EDGECOLOR = 'figedgecolor'
    FIGURE_ALPHA = 'figalpha'
    FIGURE_PADDING = 'figpadding'
    
    # Axis
    X_LABEL = 'xlabel'
    Y_LABEL = 'ylabel'
    AXES_TITLE ='axestitle'
    X_LIM_LOWER = 'xlimlower'
    X_LIM_UPPER = 'xlimupper'
    Y_LIM_LOWER = 'ylimlower'
    Y_LIM_UPPER = 'ylimupper'
    X_SCALE = 'xscale'
    Y_SCALE = 'yscale'
    # Line
    LINE_WIDTH = 'linewidth'
    LINE_STYLE = 'linestyle'
    LINE_COLOR = 'linecolor'
    MARKER = 'marker'
    MARKER_SIZE = 'markersize'
    MARKER_FACECOLOR = 'markerfacecolor'
    MARKER_EDGECOLOR = 'markeredgecolor'
    MARKER_EDGEWIDTH = 'markeredgewidth'
    #Line Alpha
    #Marker alpha
    #Dash pattern
    # Line antialiased
    # label for legend
    # custom marker path
    # z-order
    # clip on, whether the line/marker is clipped to axes
    # pick radius
    
    
    #FONT
    FONT_SIZE = 'fontsize'
 
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

    def handle_suptitle(self, fig, value):
        fig.suptitle(value)
        
    def handle_figfacecolor(self, fig, value):
        fig.set_facecolor(value)
        
    def handle_figedgecolor(self, fig, value):
        fig.patch.set_edgecolor(value)
        fig.patch.set_linewidth(5)

    def handle_figalpha(self, fig, value):
        fig.patch.set_alpha(value)
    
    def handle_figpadding(self, fig, value):
        fig.subplots_adjust(left=value, right=1-value, top=1-value, bottom=value)
        
    # Axis
    def handle_xlabel(self, ax, value):
        ax.set_xlabel(value)
    
    def handle_ylabel(self, ax, value):
        ax.set_ylabel(value)

    def handle_axestitle(self, ax, value):
        ax.set_title(value)
        
    def handle_xlimlower(self, ax, value):
        ax.set_xlim(left=value)
        
    def handle_xlimupper(self, ax, value):
        ax.set_xlim(right=value)

    def handle_ylimlower(self, ax, value):
        ax.set_ylim(bottom=value)
        
    def handle_ylimupper(self, ax, value):
        ax.set_ylim(top=value)
    
    def handle_xscale(self, ax, value):
        ax.set_xscale(value)
    
    def handle_yscale(self, ax, value):
        ax.set_yscale(value)    
    
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
    def handle_xticks(self, ax, value):
        ax.set_xticks(value)

    def handle_yticks(self, ax, value):
        ax.set_yticks(value)
        
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
        
    def handle_markersize(self, line, value):
        line.set_markersize(value)
        
    def handle_markerfacecolor(self, line, value):
        line.set_markerfacecolor(value)
        
    def handle_markeredgecolor(self, line, value):
        line.set_markeredgecolor(value)

    def handle_markeredgewidth(self, line, value):
        line.set_markeredgewidth(value)

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
        
        self.plot_config_hdlr = PlotConfigHandler()
        self.cfg_key = PlotConfigKey()
    
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
        self.figure_width = QtWidgets.QDoubleSpinBox()
        self.figure_width.setValue(10)
        self.figure_width.editingFinished.connect(self.ui_config_figsize_changed)
        self.figure_height = QtWidgets.QDoubleSpinBox()
        self.figure_height.setValue(10)
        self.figure_height.editingFinished.connect(self.ui_config_figsize_changed)
        layout.addRow(QtWidgets.QLabel("Width:"),self.figure_width)
        layout.addRow(QtWidgets.QLabel("Height:"),self.figure_height)
        
        # DPI setting
        self.dpi_spinbox = QtWidgets.QSpinBox()
        self.dpi_spinbox.setRange(50, 300)
        self.dpi_spinbox.setValue(100)
        self.dpi_spinbox.editingFinished.connect(self.ui_config_dpi_changed)
        layout.addRow(QtWidgets.QLabel("DPI:"), self.dpi_spinbox)
        
        # Figure title setting
        self.fig_title_input = QtWidgets.QLineEdit()
        self.fig_title_input.editingFinished.connect(self.ui_config_suptitle_changed)
        layout.addRow(QtWidgets.QLabel("Figure Title:"), self.fig_title_input)
        
        # Face color setting
        self.facecolor_button = QtWidgets.QPushButton("C")
        self.facecolor_button.clicked.connect(self.choose_fig_face_color)
        self.facecolor_value = QtWidgets.QLineEdit("white")  # Display the selected color
        self.facecolor_value.textChanged.connect(self.ui_config_figfacecolor_changed)
        layout_facecolor = QtWidgets.QHBoxLayout()
        layout_facecolor.addWidget(self.facecolor_value)
        layout_facecolor.addWidget(self.facecolor_button)       
        layout.addRow(QtWidgets.QLabel("Face Color:"), layout_facecolor)
        
        # Edge color setting
        self.edgecolor_button = QtWidgets.QPushButton("C")
        self.edgecolor_button.clicked.connect(self.choose_fig_edge_color)
        self.edgecolor_value = QtWidgets.QLineEdit("black")  # Display the selected color
        self.edgecolor_value.textChanged.connect(self.ui_config_figedgecolor_changed)
        layout_edgecolor = QtWidgets.QHBoxLayout()
        layout_edgecolor.addWidget(self.edgecolor_value)
        layout_edgecolor.addWidget(self.edgecolor_button)
        layout.addRow(QtWidgets.QLabel("Edge Color:"), layout_edgecolor)
        
        # Transparency
        self.figure_transparency = QtWidgets.QDoubleSpinBox()
        self.figure_transparency.setValue(1)
        self.figure_transparency.setRange(0,1)
        self.figure_transparency.editingFinished.connect(self.ui_config_figtransparency_changed)
        layout.addRow(QtWidgets.QLabel("Transparency:"),self.figure_transparency)

        # Padding
        self.figure_padding = QtWidgets.QDoubleSpinBox()
        self.figure_padding.setValue(0.1)
        self.figure_padding.setRange(0,0.45)
        self.figure_padding.editingFinished.connect(self.ui_config_figpadding_changed)
        layout.addRow(QtWidgets.QLabel("Padding:"),self.figure_padding)
        
        return group_widget

    def create_axes_config_group(self):
        """Create a QWidget for axes configurations."""
        group_widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(group_widget)
        
        # Axes title
        self.axes_title_input = QtWidgets.QLineEdit()
        self.axes_title_input.editingFinished.connect(self.ui_config_axestitle_changed)
        layout.addRow(QtWidgets.QLabel("Axes Title:"), self.axes_title_input)
        
        # Axis label
        self.xlabel_input = QtWidgets.QLineEdit()
        self.xlabel_input.editingFinished.connect(self.ui_config_xlabel_changed)
        self.ylabel_input = QtWidgets.QLineEdit()
        self.ylabel_input.editingFinished.connect(self.ui_config_ylabel_changed)
        layout.addRow(QtWidgets.QLabel("X-axis Label:"), self.xlabel_input)
        layout.addRow(QtWidgets.QLabel("Y-axis Label:"), self.ylabel_input)

        # Axis limits
        self.xlim_min_input = SimplifiedNumberLineEditor()
        self.xlim_min_input.validTextChanged.connect(self.ui_config_xlimlower_changed)
        self.xlim_max_input = SimplifiedNumberLineEditor()
        self.xlim_max_input.validTextChanged.connect(self.ui_config_xlimupper_changed)
        self.ylim_min_input = SimplifiedNumberLineEditor()
        self.ylim_min_input.validTextChanged.connect(self.ui_config_ylimlower_changed)
        self.ylim_max_input = SimplifiedNumberLineEditor()
        self.ylim_max_input.validTextChanged.connect(self.ui_config_ylimupper_changed)
        layout.addRow(QtWidgets.QLabel("X-axis Min:"), self.xlim_min_input)
        layout.addRow(QtWidgets.QLabel("X-axis Max:"), self.xlim_max_input)
        layout.addRow(QtWidgets.QLabel("Y-axis Min:"), self.ylim_min_input)
        layout.addRow(QtWidgets.QLabel("Y-axis Max:"), self.ylim_max_input)

        # Scale
        self.xlog_scale = QtWidgets.QComboBox()
        self.xlog_scale.addItems(['linear','log'])
        self.xlog_scale.currentIndexChanged.connect(self.ui_config_xscale_changed)
        self.ylog_scale = QtWidgets.QComboBox()
        self.ylog_scale.addItems(['linear','log'])
        self.ylog_scale.currentIndexChanged.connect(self.ui_config_yscale_changed)
        layout.addRow(QtWidgets.QLabel("X-Scale:"), self.xlog_scale)
        layout.addRow(QtWidgets.QLabel("Y-Scale:"), self.ylog_scale)
        
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
        self.linewidth_spinbox.valueChanged.connect(self.ui_config_linewidth_changed)
        layout.addRow(QtWidgets.QLabel("Line Width:"), self.linewidth_spinbox)

        # Line style setting
        self.linestyle_combobox = QtWidgets.QComboBox()
        self.linestyle_combobox.addItems(['-', '--', '-.', ':', 'None'])
        self.linestyle_combobox.currentIndexChanged.connect(self.ui_config_linestyle_changed)
        layout.addRow(QtWidgets.QLabel("Line Style:"), self.linestyle_combobox)

        # Line color setting
        self.linecolor_button = QtWidgets.QPushButton("C")
        self.linecolor_button.clicked.connect(self.choose_line_color)
        self.linecolor_value = QtWidgets.QLineEdit("black")  # Display the selected color
        self.linecolor_value.textChanged.connect(self.ui_config_linecolor_changed)
        layout_linecolor =  QtWidgets.QHBoxLayout()
        layout_linecolor.addWidget(self.linecolor_value)
        layout_linecolor.addWidget(self.linecolor_button)
        layout.addRow(QtWidgets.QLabel("Line Color:"), layout_linecolor)

        # Marker style setting
        self.marker_combobox = QtWidgets.QComboBox()
        marker_list = ['None','.','o','v','^','<','>','1','2','3','4','8','s','p','*','h','H','+','x','D','d','|','_','P','X']
        self.marker_combobox.addItems(marker_list)
        self.marker_combobox.currentIndexChanged.connect(self.ui_config_marker_changed)
        layout.addRow(QtWidgets.QLabel("Marker Style:"), self.marker_combobox)

        # Marker size setting
        self.marker_size_spinbox = QtWidgets.QSpinBox()
        self.marker_size_spinbox.setRange(1, 20)
        self.marker_size_spinbox.setValue(6)
        self.marker_size_spinbox.valueChanged.connect(self.ui_config_marker_size_changed)
        layout.addRow(QtWidgets.QLabel("Marker Size:"), self.marker_size_spinbox)
        
        # Marker Face Color setting
        self.markerfacecolor_button = QtWidgets.QPushButton("C")
        self.markerfacecolor_button.clicked.connect(self.choose_marker_face_color)
        self.markerfacecolor_value = QtWidgets.QLineEdit("red")  # Display the selected color
        self.markerfacecolor_value.textChanged.connect(self.ui_config_marker_face_color_changed)       
        layout_markerfacecolor = QtWidgets.QHBoxLayout()
        layout_markerfacecolor.addWidget(self.markerfacecolor_value)
        layout_markerfacecolor.addWidget(self.markerfacecolor_button)        
        layout.addRow(QtWidgets.QLabel("Marker Face Color:"), layout_markerfacecolor)
        
        # Marker Edge Width setting
        self.marker_edgewidth_spinbox = QtWidgets.QSpinBox()
        self.marker_edgewidth_spinbox.setRange(1, 10)  # Set the range for edge width
        self.marker_edgewidth_spinbox.setValue(1)      # Default value
        self.marker_edgewidth_spinbox.valueChanged.connect(self.ui_config_marker_edgewidth_changed)      
        layout.addRow(QtWidgets.QLabel("Marker Edge Width:"), self.marker_edgewidth_spinbox)
      
        # Marker Edge Color setting
        self.markeredgecolor_button = QtWidgets.QPushButton("C")
        self.markeredgecolor_button.clicked.connect(self.choose_marker_edge_color)
        self.markeredgecolor_value = QtWidgets.QLineEdit("black")  # Display the selected color
        self.markeredgecolor_value.textChanged.connect(self.ui_config_marker_edge_color_changed)
        layout_markeredgecolor = QtWidgets.QHBoxLayout()
        layout_markeredgecolor.addWidget(self.markeredgecolor_value)
        layout_markeredgecolor.addWidget(self.markeredgecolor_button)     
        layout.addRow(QtWidgets.QLabel("Marker Edge Color:"), layout_markeredgecolor)

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
    
    def choose_fig_face_color(self):
        """Open a color dialog to choose the figure face color."""
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.facecolor_value.setText(color.name())  # Update the label text

    def choose_fig_edge_color(self):
        """Open a color dialog to choose the figure edge color."""
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.edgecolor_value.setText(color.name())  # Update the label text

    def choose_line_color(self):
        """Open a color dialog to choose the line color."""
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.linecolor_value.setText(color.name())  # Update the label text
            
    def choose_marker_face_color(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.markerfacecolor_value.setText(color.name())
    
    def choose_marker_edge_color(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.markeredgecolor_value.setText(color.name())


    """ @SLOTS of UI Widgets"""
    def update_whole_figure(self):
        self.obj_fig.tight_layout()
        self.obj_fig.canvas.draw()
        
    # Figure
    def ui_config_figsize_changed(self):
        if self.obj_fig:
            fig_width = self.figure_width.value()
            fig_height = self.figure_height.value()
            self.plot_config_hdlr.set_obj_key_value(self.obj_fig, self.cfg_key.FIGURE_SIZE, (fig_width, fig_height))
            self.update_whole_figure()
    
    def ui_config_dpi_changed(self):
        if self.obj_fig:
            dpi = self.dpi_spinbox.value()
            self.plot_config_hdlr.set_obj_key_value(self.obj_fig, self.cfg_key.DPI, dpi)
            self.update_whole_figure()
    
    def ui_config_suptitle_changed(self):
        if self.obj_fig:
            sup_title = self.fig_title_input.text()
            self.plot_config_hdlr.set_obj_key_value(self.obj_fig, self.cfg_key.FIGURE_TITLE, sup_title)
            self.update_whole_figure()
            
    def ui_config_figfacecolor_changed(self):
        if self.obj_fig:
            fig_face_color = self.facecolor_value.text()
            self.plot_config_hdlr.set_obj_key_value(self.obj_fig, self.cfg_key.FIGURE_FACECOLOR, fig_face_color)
            self.update_whole_figure()
            
    def ui_config_figedgecolor_changed(self):
        if self.obj_fig:
            fig_edge_color = self.edgecolor_value.text()
            self.plot_config_hdlr.set_obj_key_value(self.obj_fig, self.cfg_key.FIGURE_EDGECOLOR, fig_edge_color)
            self.update_whole_figure()
    
    def ui_config_figtransparency_changed(self):
        if self.obj_fig:
            fig_alpha = self.figure_transparency.value()
            self.plot_config_hdlr.set_obj_key_value(self.obj_fig, self.cfg_key.FIGURE_ALPHA, fig_alpha)
            self.update_whole_figure()
            
    def ui_config_figpadding_changed(self):
        if self.obj_fig:
            fig_padding = self.figure_padding.value()
            self.plot_config_hdlr.set_obj_key_value(self.obj_fig, self.cfg_key.FIGURE_PADDING, fig_padding)
            self.update_whole_figure()
        
    # Axis
    def ui_config_axestitle_changed(self):
        if self.obj_axis:
            axes_title = self.axes_title_input.text()
            self.plot_config_hdlr.set_obj_key_value(self.obj_axis, self.cfg_key.AXES_TITLE, axes_title)
            self.update_whole_figure()
            
    def ui_config_xlabel_changed(self):
        if self.obj_axis:
            x_label = self.xlabel_input.text()
            self.plot_config_hdlr.set_obj_key_value(self.obj_axis, self.cfg_key.X_LABEL, x_label)
            self.update_whole_figure()
            
    def ui_config_ylabel_changed(self):
        if self.obj_axis:
            y_label = self.ylabel_input.text()
            self.plot_config_hdlr.set_obj_key_value(self.obj_axis, self.cfg_key.Y_LABEL, y_label)
            self.update_whole_figure()
            
    def ui_config_xlimlower_changed(self):
        if self.obj_axis:
            x_lim_lower = self.xlim_min_input.value()
            self.plot_config_hdlr.set_obj_key_value(self.obj_axis, self.cfg_key.X_LIM_LOWER, x_lim_lower)
            self.update_whole_figure()
    
    def ui_config_xlimupper_changed(self):
        if self.obj_axis:
            x_lim_upper = self.xlim_max_input.value()
            self.plot_config_hdlr.set_obj_key_value(self.obj_axis, self.cfg_key.X_LIM_UPPER, x_lim_upper)
            self.update_whole_figure()
            
    def ui_config_ylimlower_changed(self):
        if self.obj_axis:
            y_lim_lower = self.ylim_min_input.value()
            self.plot_config_hdlr.set_obj_key_value(self.obj_axis, self.cfg_key.Y_LIM_LOWER, y_lim_lower)
            self.update_whole_figure()
    
    def ui_config_ylimupper_changed(self):
        if self.obj_axis:
            y_lim_upper = self.ylim_max_input.value()
            self.plot_config_hdlr.set_obj_key_value(self.obj_axis, self.cfg_key.Y_LIM_UPPER, y_lim_upper)
            self.update_whole_figure()
    
    def ui_config_xscale_changed(self):
        if self.obj_axis:
            x_scale = self.xlog_scale.currentText()
            self.plot_config_hdlr.set_obj_key_value(self.obj_axis, self.cfg_key.X_SCALE, x_scale)
            self.update_whole_figure()
    
    def ui_config_yscale_changed(self):
        if self.obj_axis:
            y_scale = self.ylog_scale.currentText()
            self.plot_config_hdlr.set_obj_key_value(self.obj_axis, self.cfg_key.Y_SCALE, y_scale)
            self.update_whole_figure()
            
    # Line    
    def ui_config_linewidth_changed(self):
        if self.obj_line:
            line_width = self.linewidth_spinbox.value()
            self.plot_config_hdlr.set_obj_key_value(self.obj_line, self.cfg_key.LINE_WIDTH, line_width)        
            self.update_whole_figure()
            
        # emit signal to plg_obj_mgr to update config in uds_data
        
    def ui_config_linestyle_changed(self):        
        if self.obj_line:
            line_style = self.linestyle_combobox.currentText()
            self.plot_config_hdlr.set_obj_key_value(self.obj_line, self.cfg_key.LINE_STYLE, line_style)
            self.update_whole_figure()
            
    def ui_config_linecolor_changed(self):
        if self.obj_line:
            line_color = self.linecolor_value.text()
            self.plot_config_hdlr.set_obj_key_value(self.obj_line, self.cfg_key.LINE_COLOR, line_color)
            self.update_whole_figure()
            
    def ui_config_marker_changed(self):
        if self.obj_line:
            marker = self.marker_combobox.currentText()
            self.plot_config_hdlr.set_obj_key_value(self.obj_line, self.cfg_key.MARKER, marker)
            self.update_whole_figure()
            
    def ui_config_marker_size_changed(self):
        if self.obj_line:
            marker_size = self.marker_size_spinbox.value()
            self.plot_config_hdlr.set_obj_key_value(self.obj_line, self.cfg_key.MARKER_SIZE, marker_size)
            self.update_whole_figure()
            
    def ui_config_marker_face_color_changed(self):
        if self.obj_line:
            color = self.markerfacecolor_value.text()
            self.plot_config_hdlr.set_obj_key_value(self.obj_line, self.cfg_key.MARKER_FACECOLOR, color)
            self.update_whole_figure()

    def ui_config_marker_edge_color_changed(self):
        if self.obj_line:
            color = self.markeredgecolor_value.text()
            self.plot_config_hdlr.set_obj_key_value(self.obj_line, self.cfg_key.MARKER_EDGECOLOR, color)
            self.update_whole_figure()
            
    def ui_config_marker_edgewidth_changed(self):
        if self.obj_line:
            marker_edgewidth = self.marker_edgewidth_spinbox.value()
            self.plot_config_hdlr.set_obj_key_value(self.obj_line, self.cfg_key.MARKER_EDGEWIDTH, marker_edgewidth)
            self.update_whole_figure()

   
    """ Regular Functions """
    def set_obj_figure(self, obj_fig):
        self.obj_fig = obj_fig
        
        # get all present fig configs
        
    def set_obj_axis(self, obj_axis):
        self.obj_axis = obj_axis
        
        # get all present axis configs
        
    def set_obj_curve(self, obj_curve):
        self.obj_line = obj_curve
        print("Current line:",self.obj_line)
        
        # get all present curve config
    
    def rgba_to_hex(self, rgba):
        r, g, b, _ = rgba  # Ignore alpha
        return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))
    
    def retrieve_current_figure_config(self):
        fig_width, fig_height = self.obj_fig.get_size_inches()
        dpi = self.obj_fig.get_dpi()
        face_color = self.obj_fig.get_facecolor()
        edge_color = self.obj_fig.get_edgecolor()
        title = self.obj_fig._suptitle.get_text() if self.obj_fig._suptitle else None
        transparent = self.obj_fig.patch.get_alpha()
        #tight_layout_pad = self.obj_fig.get_tight_layout()  # True/False
        bbox_inches = self.obj_fig.subplotpars  # padding info
        
        # update
        self.figure_width.setValue(fig_width)
        self.figure_height.setValue(fig_height)
        self.dpi_spinbox.setValue(dpi)
        if title:
            self.fig_title_input.setText(title)
        else:
            self.fig_title_input.setText('')
        self.facecolor_value.setText(self.rgba_to_hex(face_color))
        self.edgecolor_value.setText(self.rgba_to_hex(edge_color))
        if transparent:
            self.figure_transparency.setValue(transparent)
        else:
            self.figure_transparency.setValue(1.0)       
        padding = (bbox_inches.wspace + bbox_inches.hspace)/2
        self.figure_padding.setValue(padding)
        
    def retrieve_current_axis_config(self):
        title = self.obj_axis.get_title()
        xlabel = self.obj_axis.get_xlabel()
        ylabel = self.obj_axis.get_ylabel()
        x_min, x_max = self.obj_axis.get_xlim()
        y_min, y_max = self.obj_axis.get_ylim()
        xscale = self.obj_axis.get_xscale()
        yscale = self.obj_axis.get_yscale()
        
        # Print them
        if title:
            self.axes_title_input.setText(title)
        else:
            self.axes_title_input.setText('')
        if xlabel:
            self.xlabel_input.setText(xlabel)
        else:
            self.xlabel_input.setText('')
        if ylabel:
            self.ylabel_input.setText(ylabel)
        else:
            self.ylabel_input.setText('')
        self.xlim_min_input.setValue(x_min)
        self.xlim_max_input.setValue(x_max)
        self.ylim_min_input.setValue(y_min)
        self.ylim_max_input.setValue(y_max) 
        if xscale == 'linear':
            self.xlog_scale.setCurrentIndex(0)
        else:
            self.xlog_scale.setCurrentIndex(1)
        if yscale == 'linear':
            self.ylog_scale.setCurrentIndex(0)
        else:
            self.ylog_scale.setCurrentIndex(1)