# -*- coding: utf-8 -*-
import numpy as np
import matplotlib as mpl
from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure

from angstrompro.utils.qt_compat import QtWidgets, QtGui


class ColorBar(QtWidgets.QWidget):
    """Thin vertical colormap preview using a matplotlib colorbar."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMaximumWidth(60)
        self.canvas = FigureCanvas(Figure(figsize=(0.5, 10), dpi=100))
        self.canvas.figure.subplots_adjust(left=0, bottom=0, right=1, top=1)
        self.canvas_ax = self.canvas.figure.add_subplot(1, 1, 1)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.setColorMap('gray')

    def setColorMap(self, cmap_name: str) -> None:
        """Render the named colormap. Works for both built-in and registered custom maps."""
        try:
            norm = mpl.colors.Normalize(vmin=0, vmax=1)
            sm = mpl.cm.ScalarMappable(cmap=cmap_name, norm=norm)
            sm.set_array([])
            self.canvas_ax.clear()
            self.canvas.figure.colorbar(sm, cax=self.canvas_ax, orientation='vertical')
            self.canvas_ax.axis('off')
            self.canvas_ax.figure.canvas.draw()
        except Exception:
            pass

    def copyToClipboard(self) -> None:
        pixmap = QtGui.QPixmap(self.canvas.size())
        self.canvas.render(pixmap)
        QtWidgets.QApplication.clipboard().setPixmap(pixmap)
