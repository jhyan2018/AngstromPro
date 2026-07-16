from .colormap_picker import ColormapPickerWidget
from .plugin_list import PluginListWidget
from .startup_module_list import StartupModuleListWidget
from .template_picker import TemplatePickerWidget
from .module_id_list import ModuleIdListWidget
from angstrompro.gui.widgets.preferences.pref_schema import register_widget_type

register_widget_type("colormap_picker",       ColormapPickerWidget)
register_widget_type("plugin_list",           PluginListWidget)
register_widget_type("startup_module_list",   StartupModuleListWidget)
register_widget_type("template_picker",       TemplatePickerWidget)
register_widget_type("module_id_list",        ModuleIdListWidget)
