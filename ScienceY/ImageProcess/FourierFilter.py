# -*- coding: utf-8 -*-
"""
Created on Thu Aug 31 16:10:44 2023

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

"""
function Module
"""

class FourierFilter():
    def __init__(self, data2D, px, py, windowType="GAUSSIAN", kSigma=1):
        self.data2D = data2D
        self.px = px
        self.py = py
        self.windowType = windowType
        self.kSigma = kSigma
            
    def fourierFilterIsolate(self):
        dataFFT = np.fft.fftshift( np.fft.fft2(self.data2D) )
        filter_window = self.getFourierFilterWindow()
        dataFFT_filtered = dataFFT * filter_window
        
        N = self.data2D.shape[-1]        
        if self.px == (N - N%2)/2 and self.py == (N - N%2)/2: # Gamma Point in q space
            data_filtered = np.real(np.fft.ifft2(np.fft.fftshift(dataFFT_filtered)) )
        else:
            data_filtered = 2 * np.real(np.fft.ifft2(np.fft.fftshift(dataFFT_filtered)) ) # factor 2 for the symmetric points
        
        return data_filtered

    def fourierFilterOut(self):
        pass

    def getFourierFilterWindow(self):
        filter_window = np.zeros_like(self.data2D)
        
        x = np.arange(filter_window.shape[-1])
        y = np.arange(filter_window.shape[-2])
        X,Y = np.meshgrid(x,y)
        
        if self.windowType == "GAUSSIAN" :
            filter_window = np.exp( - ( ( X - self.px ) ** 2 + ( Y - self.py ) ** 2 ) 
                                      / ( 2 * self.kSigma ** 2 ) )
        else:
            pass
        
        return filter_window