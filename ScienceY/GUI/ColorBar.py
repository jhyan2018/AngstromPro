# -*- coding: utf-8 -*-
"""
Created on Tue Apr 16 15:01:05 2024

@author: jiahaoYan
"""


"""
System modules
"""
import os

"""
Third-party Modules
"""
import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure
from matplotlib import colors
import matplotlib as mpl

"""
User Modules
"""

"""
Modules Definition
"""
class ColorBar(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(ColorBar, self).__init__( *args, **kwargs)
        
        self.initUiMembers()        
        self.initUiLayout()
        self.initNonUiMembers()
    
    def initUiMembers(self):
        self.canvas = FigureCanvas(Figure(figsize=(0.5, 10), dpi = 100))
        self.canvas.figure.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=None, hspace=None)
        self.canvas_ax = self.canvas.figure.add_subplot(1,1,1)
     
        self.setColorMap('magma', 0)       
    
    def initUiLayout(self):
        ui_horizontalLayout1 = QtWidgets.QHBoxLayout()
        ui_horizontalLayout1.addWidget(self.canvas)

        
        ui_gridlayout = QtWidgets.QGridLayout()
        ui_gridlayout.addLayout(ui_horizontalLayout1, 0, 0, 1, 1)
        #ui_gridlayout.setContentsMargins(0,0,0,0) # left, top, right, bottom
        
        self.setLayout(ui_gridlayout) 
    
    def initNonUiMembers(self):
        self.customizedColorPalletFolder = './ScienceY/GUI/customizedColorPallets/'
        
    def setColorMap(self,cmap, ctype):
        colormap = cmap
        
        if ctype == 0: # built-in cmap
            colormap = cmap            
        else: # customized cmap
            colormap = self.make_colormap(cmap)
        
        # Create a ScalarMappable with the colormap
        norm = mpl.colors.Normalize(vmin=0, vmax=1)
        sm = mpl.cm.ScalarMappable(cmap=colormap, norm=norm)
        sm.set_array([])  # You need to set_array for ScalarMappable
        
        self.canvas_ax.clear()
        self.canvas.figure.colorbar(sm, cax=self.canvas_ax, orientation='vertical')
        self.canvas_ax.axis('off')
        self.canvas_ax.figure.canvas.draw()
    
    def make_colormap( self, cp ):
        s = self.customizedColorPalletFolder
        path = s + cp + '.txt'
        #path = '/Users/Kazu/Documents/kpython/KFViewPyII/Color Palette/blue2.txt'
        d = np.loadtxt( path, delimiter = "\t", skiprows = 1 ) / 256 / 256

        cdict = {'red': [], 'green': [], 'blue': [] }
        for i in range( 0,256 ):
            cdict[ 'red' ].append( [ i / 255.0, d[ i, 0 ], d[ i, 0 ] ] )
            cdict[ 'green' ].append( [ i / 255.0, d[ i, 1 ], d[ i, 1 ] ] )
            cdict[ 'blue' ].append( [ i / 255.0, d[ i, 2 ], d[ i, 2 ] ] )
        return colors.LinearSegmentedColormap( 'CustomMap', cdict )
    
    def copyToClipboard(self):
        pixmap = QtGui.QPixmap(self.canvas.size())
        self.canvas.render(pixmap)
        QtWidgets.QApplication.clipboard().setPixmap(pixmap)
        
    def copyToPixmap(self):
        pixmap = QtGui.QPixmap(self.canvas.size())
        self.canvas.render(pixmap)
        
        return pixmap
    