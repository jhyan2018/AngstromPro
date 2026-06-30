from .colormap_picker import ColormapPickerWidget
from angstrompro.gui.widgets.preferences.pref_schema import register_widget_type

register_widget_type("colormap_picker", ColormapPickerWidget)
