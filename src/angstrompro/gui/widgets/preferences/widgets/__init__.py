from .colormap_picker import ColormapPickerWidget
from .plugin_list import PluginListWidget
from .startup_module_list import StartupModuleListWidget
from angstrompro.gui.widgets.preferences.pref_schema import register_widget_type

register_widget_type("colormap_picker",       ColormapPickerWidget)
register_widget_type("plugin_list",           PluginListWidget)
register_widget_type("startup_module_list",   StartupModuleListWidget)
