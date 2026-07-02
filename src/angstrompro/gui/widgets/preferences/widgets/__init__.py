from .colormap_picker import ColormapPickerWidget
from .plugin_list import PluginListWidget
from angstrompro.gui.widgets.preferences.pref_schema import register_widget_type

register_widget_type("colormap_picker", ColormapPickerWidget)
register_widget_type("plugin_list",     PluginListWidget)
