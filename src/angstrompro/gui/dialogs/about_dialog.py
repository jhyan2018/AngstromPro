# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 2026

@author: jiahaoYan
"""

from __future__ import annotations

from datetime import datetime

from angstrompro.utils.qt_compat import QtWidgets


def show_about(parent: QtWidgets.QWidget | None = None) -> None:
    from angstrompro.core.configs.defaults.app import DEFAULTS as _APP_DEFAULTS
    version = _APP_DEFAULTS.get("version", "unknown")
    current_year = str(datetime.now().year)
    QtWidgets.QMessageBox.about(
        parent,
        "About AngstromPro",
        f"AngstromPro v{version}\n\n"
        "Created by Huiyu Zhao & Jiahao Yan\n"
        f"© 2023 – {current_year}\n\n"
        "Data management, visualization, processing & simulation\n"
        "software for STM.\n\n"
        "Built on Matplotlib and Qt.",
    )
