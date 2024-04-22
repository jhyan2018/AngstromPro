# -*- coding: utf-8 -*-
"""
Created on Wed Sep 13 14:03:55 2023

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
from ..ImageSimulate.GenerateCurve2D import gaussian2D
"""
function Module
"""

class LockIn2D():
    def __init__(self, data2D, px, py, rSigma): # data2D should be a square matrix
               
        # calculate equivalent k-space Gaussian function with respect to r-space Gaussian
        N = data2D.shape[-1]
        kSigma = N / (2 * np.pi * rSigma)
        kFactor = 2 * np.pi * (rSigma**2)
        #print("2D Lockin KSigma:", kSigma)
        
        kGaussian = kFactor * gaussian2D(N, kSigma)
        
        # calculate A_Q(k)
        O_kx = (N - N%2)/2
        O_ky = (N - N%2)/2
        
        Qx = 2 * np.pi * (px - O_kx) / N
        Qy = 2 * np.pi * (py - O_ky) / N
        
        x = np.arange(N)
        y = np.arange(N)
        X,Y = np.meshgrid(x,y)
        
        eQR = np.exp( 1j * ( Qx * X + Qy * Y) )
        
        A_Q_k = np.fft.fftshift( np.fft.fft2( data2D * eQR ) )
        
        # calculate A_Q(r)
        self.A_Q_r =np.fft.ifft2( np.fft.fftshift( A_Q_k * kGaussian ) ) 
    
    def phaseUnwrap(self, phaseReverseFactor=0.8):
        #phaseMapWrapped = np.arctan2( np.imag(self.A_Q_r), np.real(self.A_Q_r) )
        phaseMapWrapped = np.angle(self.A_Q_r)
        phaseMapRegions = np.zeros_like(phaseMapWrapped)
        
        for col in range(self.A_Q_r.shape[-1]):
            n = 0
            for row in range(self.A_Q_r.shape[-2] - 1):
                if phaseMapWrapped[row+1,col] * phaseMapWrapped[row,col] <  - phaseReverseFactor * np.pi**2 :
                    if phaseMapWrapped[row+1,col] > 0:
                        n -= 1
                    else:
                        n += 1
                phaseMapRegions[row+1,col] = n
        
        phaseMapRegions[0,:] = phaseMapRegions[1,:]
        
        phaseMapUnwrapped = phaseMapWrapped + 2*np.pi*phaseMapRegions
        
        return phaseMapUnwrapped
    
    def getPhaseMap(self, phaseUnwrap=True, phaseReverseFactor=0.8):
        phaseMap = np.arctan2( np.imag(self.A_Q_r), np.real(self.A_Q_r) )
        
        if phaseUnwrap == True:
            phaseMap = self.phaseUnwrap(phaseReverseFactor)
            
        return phaseMap
               
    def getAmplitudeMap(self):
        return np.abs( self.A_Q_r )
    
