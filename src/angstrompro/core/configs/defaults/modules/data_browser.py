DEFAULTS = {
    # Watched measurement folders; none may be a subfolder of another.
    "watch_folders": [],
    "formats": {
        # formats shown in the gallery / scanned in the background;
        # "*" = every readable format, including plugin formats added later
        "watched": ["*"],
    },
    "scanner": {
        "enabled": True,
        "request_interval": 1.5,    # s between background render requests
        "idle_interval": 60.0,      # s between full passes
        "order": "newest_first",    # newest_first | oldest_first | name
    },
    "thumbnails": {
        "size": 150,                # card image px; also render figure size
        "stack_threshold": 10,      # >N curves → colormap branch
        "template": "",             # curve-stack template name; "" = none
        "pixmap_cache_size": 200,   # decoded thumbnails kept in memory
    },
    "cache": {
        "cleanup_orphans": True,    # sweep crash-leftover PNGs at startup
    },
}
