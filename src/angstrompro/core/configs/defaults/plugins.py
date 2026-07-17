DEFAULTS = {
    # List of dicts, each with:
    #   "path"   : absolute path to the plugin's src/ folder (added to sys.path)
    #   "module" : top-level module name to import (triggers @register_process / @register_module)
    # These load before entry-point plugins.
    "path_plugins": [],
}
