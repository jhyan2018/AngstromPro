DEFAULTS = {
    "version": "1.2.0",
    "debug_mode": False,
    "strict_process_menu": True,   # skip incompatible processes in module menus; False = add with warning
    # Modules to auto-create at startup, before the main workbench is shown.
    # Each entry: {"module_id": "image_stack_viewer", "count": 1}
    "startup_modules": [
        {"module_id": "image_stack_viewer", "count": 1},
    ],
}
