# -*- coding: utf-8 -*-
"""
Created on Fri Sep 15 16:06:38 2023

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

def sinusoidal2D(size, qx, qy, phase, amplitude=1): #qx and qy is in pixels relative to center of data size
    x = np.arange(size)
    y = np.arange(size)
    X,Y = np.meshgrid(x,y)

    # cos(a+b) = cos(a)sin(b) - sin(a)sin(b)
    # cos(qr-phi) = cos(qr)cos(phi) + sin(qr)sin(phi)
    sinusoidalCurve = amplitude * np.cos( 2*np.pi*(qx/size) * X + 2*np.pi*(qy/size) * Y - phase)
    
    return sinusoidalCurve

def gaussian2D(size, sigma, center_x=None, center_y=None):
    x = np.arange(size)
    y = np.arange(size)
    X,Y = np.meshgrid(x,y)
    
    if center_x == None:
        center_x = (size - size%2)/2
    else:
        center_x += (size - size%2)/2
        
    if center_y == None:
        center_y = (size - size%2)/2
    else:
        center_y += (size - size%2)/2
    
    gaussianCurve = np.exp( - ( ( X - center_x ) ** 2 + ( Y - center_y ) ** 2 ) 
                              / ( 2 * sigma ** 2 ) )
    
    return gaussianCurve

def circle2D(size, radius, center_x=None, center_y=None):
    x = np.arange(size)
    y = np.arange(size)
    X,Y = np.meshgrid(x,y)
    
    if center_x == None:
        center_x = (size - size%2)/2
    else:
        center_x += (size - size%2)/2
        
    if center_y == None:
        center_y = (size - size%2)/2
    else:
        center_y += (size - size%2)/2
    
    circelCurve = (np.sqrt( ( X - center_x ) ** 2 + ( Y - center_y ) ** 2 ) < radius).astype(int)
    
    return circelCurve