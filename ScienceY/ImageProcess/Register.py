# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 11:19:50 2024

@author: Huiyu
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
from .GeometricOperation import AffineTransform

"""
function Module
"""

def Register(data3D, register_points, register_points_reference):
    '''
    Parameters
    ----------
    data3D : three dimensional data need to be registered
       from the main window
    
    '''
    rPoints = np.concatenate((register_points, register_points_reference), axis=0)
    
    affine = AffineTransform()
    affine.setAffineMatrixFrom3PairsRpoints(rPoints)
    
    affine.srcMappedPoints(data3D.shape[-2], data3D.shape[-1])
    
    data_processed = np.zeros_like(data3D)
    
    for i in range(data3D.shape[0]):
        data_processed[i,:,:] = affine.affineMappingForRegister(data3D[i,:,:],'bilinear','constant')

    return data_processed
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    