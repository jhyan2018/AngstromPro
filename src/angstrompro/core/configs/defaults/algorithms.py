DEFAULTS = {
    "default_interpolation": "linear",
    "use_gpu": False,
    "precision": "float32",

    # Developer-curated process menu entries per module_id.
    # These are the defaults shipped with the package.
    # Add entries here when you register a new built-in process.
    "process_menus": {
        "image2u3": [
            "spatial.crop2d",
        ],
        "plot1u2": [],
    },

    # User additions to process menus per module_id.
    # Users override this key in their config.json to append
    # their own registered algorithms to any module menu.
    # These are merged (appended) on top of process_menus above.
    "user_process_menus": {},
}
