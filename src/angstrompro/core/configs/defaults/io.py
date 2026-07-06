DEFAULTS = {
    "default_open_dir": "",
    "default_save_dir": "",
    "channel_manager": {
        "nanonis_3ds": {
            "__auto_load__": False,
            "dI/dV":      {"aliases": ["LI Demod"],                                 "load_by_default": True},
            "dI/dV (Y)":  {"aliases": ["LI Demod 1 Y", "LI Demod 2 Y"],            "load_by_default": False},
            "Current":    {"aliases": ["Current (A)", "Current", "I (A)"],          "load_by_default": False},
            "Z":          {"aliases": ["Z (m)", "Topo"],                            "load_by_default": False},
        },
        "nanonis_sxm": {
            "__auto_load__": False,
            "Z":          {"aliases": ["Z (m)", "Topo", "Z_fwd"],                  "load_by_default": True},
            "Current":    {"aliases": ["Current (A)", "Current", "I (A)"],          "load_by_default": False},
            "dI/dV":      {"aliases": ["LI Demod 1 X", "dI/dV", "Input 2"],        "load_by_default": False},
            "dI/dV (Y)":  {"aliases": ["LI Demod 1 Y"],                             "load_by_default": False},
        },
        "nanonis_dat": {
            "__auto_load__": False,
            "Current":    {"aliases": ["Current (A)", "Current"],                   "load_by_default": True},
            "dI/dV":      {"aliases": ["LI Demod 1 X (A)", "LI Demod 1 X"],        "load_by_default": True},
            "dI/dV (Y)":  {"aliases": ["LI Demod 1 Y (A)", "LI Demod 1 Y"],        "load_by_default": False},
            "Z":          {"aliases": ["Z (m)", "Z"],                               "load_by_default": False},
        },
    },
}
