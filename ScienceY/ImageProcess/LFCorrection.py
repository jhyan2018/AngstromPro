# -*- coding: utf-8 -*-
"""
Created on Fri Sep  8 13:49:34 2023

@author: Jiahao Yan
"""
"""
System modules
"""

"""
Third-party Modules
"""
import numpy as np
"""
User Modules
"""
from .LockIn2D import LockIn2D
from .PixelInterpolation import PixelInterpolation

"""
function Module
"""
class LFCorrection():
    def __init__(self, data2D, bPx1, bPy1, bPx2, bPy2, rSigma):
        self.data2D = data2D
        self.bPx1 = bPx1
        self.bPy1 = bPy1
        self.bPx2 = bPx2
        self.bPy2 = bPy2
        self.rSigma = rSigma
    
    def calculateDisplacementField(self):
        lockin1 = LockIn2D(self.data2D, self.bPx1, self.bPy1, self.rSigma)
        phaseMap1 = lockin1.getPhaseMap()
        
        lockin2 = LockIn2D(self.data2D, self.bPx2, self.bPy2, self.rSigma)
        phaseMap2 = lockin2.getPhaseMap()
        
        #
        N = self.data2D.shape[-1]
        
        O_kx = (N - N%2)/2
        O_ky = (N - N%2)/2
        
        bQ1x = 2 * np.pi * (self.bPx1 - O_kx) / N
        bQ1y = 2 * np.pi * (self.bPy1 - O_ky) / N
        bQ2x = 2 * np.pi * (self.bPx2 - O_kx) / N
        bQ2y = 2 * np.pi * (self.bPy2 - O_ky) / N
        
        Q_M = np.array([ [bQ1x, bQ1y], [bQ2x, bQ2y] ])
        Q_M_inv = np.linalg.inv(Q_M)
        
        ux = Q_M_inv[0,0]*(-phaseMap1) + Q_M_inv[0,1]*(-phaseMap2)
        uy = Q_M_inv[1,0]*(-phaseMap1) + Q_M_inv[1,1]*(-phaseMap2)
        
        displacementField = np.ndarray((2,N,N))
        displacementField[0,:,:] = ux
        displacementField[1,:,:] = uy
        
        return displacementField     
        
    def setDisplacementField(self, displacementField):
        self.ux = displacementField[0,:,:]
        self.uy = displacementField[1,:,:]
    
    def lFcorrection(self, interpolate_method='bilinear', pad_method='constant'):
        x = np.arange(self.data2D.shape[-1])
        y = np.arange(self.data2D.shape[-2])
        X,Y = np.meshgrid(x,y)
        
        X_df = X - self.ux
        Y_df = Y - self.uy
        
        # interpolation
        px_itp = PixelInterpolation(self.data2D, X_df, Y_df, interpolate_method, pad_method)
        corrected_data = px_itp.dataMapping()
        
        return corrected_data