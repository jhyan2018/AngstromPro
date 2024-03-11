# -*- coding: utf-8 -*-
"""
Created on Fri Sep 15 15:08:15 2023

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
from ..RawDataProcess.UdsDataStru import UdsDataStru3D

from .GenerateCurve2D import circle2D, gaussian2D, sinusoidal2D
from .GenerateLattice2D import GenerateLattice2D

"""
function Module
"""
def ismGenerateHeaviside2D(size, edge_x, edge_y):
    
    data_simulated = np.ones((size,size))
    
    data_simulated[0:edge_y, 0:edge_x] = np.zeros((edge_y, edge_x))
    
    uds3D_data_simulated = UdsDataStru3D(data_simulated[np.newaxis,:,:], 'uds3D_Heaviside2D')
    
    return uds3D_data_simulated

def ismGenerateCircle2D(size, radius, center_x, center_y):
    data_simulated = circle2D(size, radius, center_x, center_y)
    
    uds3D_data_simulated = UdsDataStru3D(data_simulated[np.newaxis,:,:], 'uds3D_Circle2D')
    
    return uds3D_data_simulated

def ismGenerateGaussian2D(size, sigma, center_x, center_y):
    data_simulated = gaussian2D(size, sigma, center_x, center_y)
    
    uds3D_data_simulated = UdsDataStru3D(data_simulated[np.newaxis,:,:], 'uds3D_Gaussian2D')
    
    return uds3D_data_simulated

def ismGenerateSinusoidal2D(size, qx, qy, phase):
    data_simulated = np.zeros((size,size))
    
    for i in range( len(qx) ):
        data_simulated += sinusoidal2D(size, qx[i], qy[i], phase[i])
    
    uds3D_data_simulated = UdsDataStru3D(data_simulated[np.newaxis,:,:], 'uds3D_Sinusoidal2D')
    
    return uds3D_data_simulated

def ismGeneratePerfectLattice2D(m, n, a1x, a1y, a2x, a2y, atomSize=None, atomCurve="Gaussian",  Ox=0, Oy=0, p1=1, p2=1):
    
    lattice2D = GenerateLattice2D(m, n, a1x, a1y, a2x, a2y, Ox, Oy)
    
    data_simulated = lattice2D.generateLattice2D(atomSize, atomCurve, p1, p2)
    
    uds3D_data_simulated = UdsDataStru3D(data_simulated[np.newaxis,:,:], 'uds3D_PerfectLattice2D')
    
    return uds3D_data_simulated

def ismGenerateLattice2DWithLineDomainWall(m, n, a1x, a1y, a2x, a2y, atomSize=None, shiftDistance=0.25, atomCurve="Gaussian",  Ox=0, Oy=0):
    
    lattice2D = GenerateLattice2D(m, n, a1x, a1y, a2x, a2y, Ox, Oy)
    lattice2D.setDisplacementLineDomainWall(shiftDistance)
    
    data_simulated = lattice2D.generateLattice2D(atomSize, atomCurve)
    
    uds3D_data_simulated = UdsDataStru3D(data_simulated[np.newaxis,:,:], 'uds3D_Lattice2D_LineDomainWall')
    
    return uds3D_data_simulated

def ismGeneratelattice2DWithPeriodicDistortion(m, n, a1x, a1y, a2x, a2y, d1x, d1y, d2x, d2y, dpA1=0.1, dpA2=0.1,
                                               atomSize=None, atomCurve="Gaussian",  Ox=0, Oy=0,
                                               dPhi1=0, dPhi2=0):

    lattice2D = GenerateLattice2D(m, n, a1x, a1y, a2x, a2y, Ox, Oy)
    lattice2D.setDisplacementPeriodic(d1x, d1y, d2x, d2y, dpA1, dpA2, dPhi1, dPhi2)
    
    data_simulated = lattice2D.generateLattice2D(atomSize, atomCurve)
    
    uds3D_data_simulated = UdsDataStru3D(data_simulated[np.newaxis,:,:], 'uds3D_Lattice2D_PeriodicDistortions')
    

    
    return uds3D_data_simulated