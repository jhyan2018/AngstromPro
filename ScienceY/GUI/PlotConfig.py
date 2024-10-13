# -*- coding: utf-8 -*-
"""
Created on Fri Oct 11 16:32:59 2024

@author: jiahaoYan
"""


"""
System modules
"""

"""
Third-party Modules
"""
import matplotlib.pyplot as plt

"""
User Modules
"""

class PlotConfig():
    def __init__(self, config_base=None):
        # Load the base configuration templates
        self.load_config_base(config_base)
        
        # Initialize figure configuration from the base config
        self.config_figure = self.config_figure_base.copy()
        
        # Initialize empty lists for axis and line configurations
        self.config_axis_list = []
        self.config_line_list = []
        
    def load_config_base(self, config_base):
        """Load the base configurations for figure, axis, and line."""
        # Base configuration for the figure
        self.config_figure_base={}
        
        # Base configuration for axes
        self.config_axis_base={}
        
        # Base configuration for lines
        self.config_line_base={'linestyle':'--',
                               'linewidth':3}
        
        if config_base:
            self.update_config_base(config_base)
        
    """ Themes """
    def update_config_base(self, config):
        self.config_figure_base.update(config.get('figure', {}))
        self.config_axis_base.update(config.get('axis', {}))
        self.config_line_base.update(config.get('line', {}))
    
    def update_config_figure_base(self,config_figure_base):
        self.config_figure_base.update(config_figure_base)
    
    def update_config_axis_base(self,config_axis_base):
        self.config_axis_base.update(config_axis_base)
    
    def update_config_line_base(self,config_line_base):
        self.config_line_base.update(config_line_base)
        
    def save_config_template_to_file(self):
        pass
    
    
    """ """
    def add_config_axis(self, new_config=None):
        """
        Add an axis configuration to the axis list.
        If new_config is provided, it updates the base configuration.
        """
        axis_config = self.config_axis_base.copy()
        if new_config:
            axis_config.update(new_config)
        self.config_axis_list.append(axis_config)
    
    def add_config_line(self, new_config=None):
        """
        Add a line configuration to the line list.
        If new_config is provided, it updates the base configuration.
        """
        line_config = self.config_line_base.copy()
        if new_config:
            line_config.update(new_config)
        self.config_line_list.append(line_config)
        
    """ Retrieving Configurations """
    def get_figure_config(self):
        return self.config_figure

    def get_axis_configs(self):
        return self.config_axis_list

    def get_line_configs(self):
        return self.config_line_list
    
    """ Set Configurations Directly"""
    def set_figure_config(self, config_figure):
        self.config_figure = config_figure.copy()
        
    def set_axis_configs(self, config_axis_list):
        self.config_axis_list = config_axis_list.copy()
        
    def set_line_configs(self, config_line_list):
        self.config_line_list = config_line_list.copy()
        
    """ Update configurations"""
    def update_figure_config(self, config):
        self.config_figure.update(config)
    
    def update_axis_config(self, ax_idx, config):
        self.config_axis_list[ax_idx].update(config)
    
    def update_line_config(self, line_idx, config):
        self.config_line_list[line_idx].update(config)
        
    """ Apply configurations"""
    def set_obj_key_value(self, obj, key, value):
        method_name = f'handle_{key}' # Build method name dynamically
        handler = getattr(self, method_name, None)
        if handler:
            handler(obj, value) # call the method if it exists
    
    def apply_figure_config(self, fig):       
        for key, value in self.config_figure.items():
            self.set_obj_key_value(fig, key, value)

    def apply_axis_config(self, ax, cfg_as_idx):
        for key, value in self.config_axis_list[cfg_as_idx].items():
            self.set_obj_key_value(ax, key, value)


    def apply_line_config(self, line, cfg_ln_idx):
        for key, value in self.config_line_list[cfg_ln_idx].items():
            self.set_obj_key_value(line, key, value)

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
    