DEFAULTS = {
    "version": "1.0.0",
    "language": "en",
    "auto_save": False,
    "debug_mode": False,
    "verbose_logging": False,
    "strict_process_menu": True,   # skip incompatible processes in module menus; False = add with warning
    # Modules to auto-create at startup, before the main workbench is shown.
    # Each entry: {"module_id": "image_stack_viewer", "count": 1}
    "startup_modules": [
        {"module_id": "image_stack_viewer", "count": 1},
    ],
}
