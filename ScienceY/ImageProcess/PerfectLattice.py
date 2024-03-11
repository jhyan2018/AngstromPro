# -*- coding: utf-8 -*-
"""
Created on Mon Aug 14 17:44:40 2023

@author: Jiahao Yan & Huiyu Zhao
"""

"""
System modules
"""
import sys, os
import itertools
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


class LatticeType():
    sampleTolatticeDict = {
        'Cuprate':'SquareLattice',
        'BSCCO':'SquareLattice',
        'NaCCOC':'SquareLattice',
        'NbSe2':'HexagonalLattice'
        }
        
    
def perfectLatticeSqure(data3D, bPx1, bPy1, bPx2, bPy2):
    affine  = AffineTransform()
    
    Ox = (data3D.shape[-1] - data3D.shape[-1]%2)/2
    Oy = (data3D.shape[-2] - data3D.shape[-2]%2)/2
    
    Q1_x = bPx1 - Ox
    Q1_y = bPy1 - Oy
    
    Q2_x = bPx2 - Ox
    Q2_y = bPy2 - Oy
    
    Q_ref_x = 0 - Ox
    Q_ref_y = 0
    
    Q1_mag = np.linalg.norm(np.array([Q1_x,Q1_y]))
    Q2_mag = np.linalg.norm(np.array([Q2_x,Q2_y]))
    Q_ref_mag = np.linalg.norm(np.array([Q_ref_x,Q_ref_y]))
    
    # angle between the Q1 and Q_ref
    theta1 = np.arccos( (Q1_x*Q_ref_x + Q1_y*Q_ref_y ) / (Q1_mag*Q_ref_mag))
    print("theta1:",theta1)
    
    # angle between the Q1 and Q2
    theta2 = np.arccos( (Q1_x*Q2_x + Q1_y*Q2_y ) / (Q1_mag*Q2_mag))
    print("theta2:",theta2)
    
    # shear
    by = 0
    if not theta2 == np.pi/2:
        by = 1/np.tan(theta2)    
    print("by:",by)
    
    # scale
    sy = Q2_mag*np.sin(theta2) / Q1_mag
    print("sy:",sy)
    
    # set Affine Parameters
    affine.setRotateOfAffineMatrix(-theta1)
    affine.setShearOfAffineMatrix(0,by)
    affine.setScaleOfAffineMatrix(1, sy)
    affine.setRotateOfAffineMatrix(np.pi/4)
    
    #
    affine.srcMappedPoints(data3D.shape[-2], data3D.shape[-1])
    
    data_processed = np.zeros((data3D.shape[0], affine.src_X_float.shape[-2], affine.src_X_float.shape[-1]))
    
    for i in range(data3D.shape[0]):
        data_processed[i,:,:] = affine.affineMapping(data3D[i,:,:],'bilinear','constant')

    return data_processed
    

def perfectLatticeHexagonal(data3D, bPx1, bPy1, bPx2, bPy2):
    # The direction from Q1 to Q2 must be clockwise and the intersection angle is around 60°

    affine  = AffineTransform()
    
    ## central point
    Ox = (data3D.shape[-1] - data3D.shape[-1]%2)/2
    Oy = (data3D.shape[-2] - data3D.shape[-2]%2)/2
    
    ## wave vector 1
    Q1_x = bPx1 - Ox
    Q1_y = bPy1 - Oy
    
    ## wave vector 2
    Q2_x = bPx2 - Ox
    Q2_y = bPy2 - Oy
    
    ## reference vector
    Q_ref_x = 0 - Ox
    Q_ref_y = Oy - Oy
    
    ## The magnitude of the wave vector
    Q1_mag = np.linalg.norm(np.array([Q1_x,Q1_y]))
    Q2_mag = np.linalg.norm(np.array([Q2_x,Q2_y]))
    Q_ref_mag = np.linalg.norm(np.array([Q_ref_x,Q_ref_y]))
    
    # angle between the Q1 and Q_ref
    theta1 = np.arccos( (Q1_x*Q_ref_x + Q1_y*Q_ref_y ) / (Q1_mag*Q_ref_mag))
    print("theta1:",theta1)
    
    if Q1_y > 0:
        theta1 = theta1
        theta = -np.pi/3
    elif Q1_y < 0:
        if theta1 > np.pi/4:
            theta1 = -theta1
            theta = np.pi/3
        else:
            theta1 = -theta1
            theta = 0
    else:
        theta1 = 0
        theta = 0
    
    # angle between the Q1 and Q2
    theta2 = np.arccos( (Q1_x*Q2_x + Q1_y*Q2_y ) / (Q1_mag*Q2_mag))
    print("theta2:",theta2)
    
    # shear
    by = 0
    if not theta2 == np.pi/3:
        by = 1/np.tan(theta2) - Q1_mag * np.cos(np.pi/3)/(Q2_mag * np.sin(theta2))
    print("by:",by)
    
    # scale
    sy = Q2_mag * np.sin(theta2)/(Q1_mag * np.sin(np.pi/3))
    print("sy:",sy)
    
    # set Affine Parameters
    affine.setRotateOfAffineMatrix(theta1)
    affine.setShearOfAffineMatrix(0, by)
    affine.setScaleOfAffineMatrix(1, sy)
    affine.setRotateOfAffineMatrix(theta)
    
    #
    affine.srcMappedPoints(data3D.shape[-2], data3D.shape[-1])
    
    data_processed = np.zeros((data3D.shape[0], affine.src_X_float.shape[-2], affine.src_X_float.shape[-1]))
    
    for i in range(data3D.shape[0]):
        data_processed[i,:,:] = affine.affineMapping(data3D[i,:,:],'bilinear','constant')

    return data_processed