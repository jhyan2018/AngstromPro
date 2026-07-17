DEFAULTS = {
    "version": "1.2.0",
    "debug_mode": False,
    "log_level": "WARNING",        # minimum level shown in the log panel: DEBUG/INFO/WARNING/ERROR
    "strict_process_menu": True,   # skip incompatible processes in module menus; False = add with warning
    # Send semantics: True = remove the item from the sender's workspace after
    # the receiver got it (move); False = keep a copy in the sender.
    "delete_after_send": True,
    # Dev/debug: show silent (internal plumbing) tasks in the task dashboard.
    # Not exposed in the preferences panel — edit via Ctrl+Shift+D config tree.
    "show_silent_tasks": False,
    # Module types (module_id) whose Workspace dock starts hidden.
    # Re-openable any time via View → Workspace (Ctrl+1).
    "hide_workspace_dock": ["data_browser"],
    # Module types (module_id) that never appear as SEND TARGETS — in the
    # send dialog and the default-targets dialog.  They can still send.
    "send_target_exclude": ["data_browser"],
    # Modules to auto-create at startup, before the main workbench is shown.
    # Each entry: {"module_id": "image_stack_viewer", "count": 1}
    "startup_modules": [
        {"module_id": "data_browser",       "count": 1},
        {"module_id": "image_stack_viewer", "count": 1},
        {"module_id": "curve_stack_viewer", "count": 1},
    ],
}
