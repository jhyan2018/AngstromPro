# -*- coding: utf-8 -*-
"""
Created on Sun Aug 13 18:19:39 2023

@author: Jiahao Yan
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
from ..RawDataProcess.UdsDataStru import UdsDataStru3D

from .BackgroundSubtract import backgroundSubtract2DPlane, backgroundSubtractPerLine
from .PerfectLattice import LatticeType
from .PerfectLattice import perfectLatticeSqure, perfectLatticeHexagonal
from .FourierFilter import FourierFilter
from .LockIn2D import LockIn2D
from .LFCorrection import LFCorrection
from .GapMap import GapMap
from .Register import Register

"""
function Module
"""

def ipBackgroundSubtract2D(uds3D_data, order=1, method='2DPlane'):
    data_processed = np.zeros_like(uds3D_data.data)
    for i in range(uds3D_data.data.shape[0]):
        if method == '2DPlane':
            data_processed[i,:,:] = backgroundSubtract2DPlane(uds3D_data.data[i,:,:], order)
        elif method == 'PerLine':
            data_processed[i,:,:] = backgroundSubtractPerLine(uds3D_data.data[i,:,:], order)  

    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_bg')
    if 'LayerValue(mV)' in uds3D_data.info.keys():
        uds3D_data_processed.info['LayerValue(mV)'] = uds3D_data.info['LayerValue(mV)'].copy()
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
            
    uds3D_data_processed.proc_history.append("ImgProc.ipBackgroundSubtract2D:order=%d" % (order))
    
    return uds3D_data_processed

def ipCropRegion2D(uds3D_data, r_topLeft, c_topLeft, r_bottomRight, c_bottomRight):
    r_side_len = r_bottomRight - r_topLeft
    c_side_len = c_bottomRight - c_topLeft
    
    data_processed = np.zeros((uds3D_data.data.shape[0], r_side_len, c_side_len))
    for i in range(uds3D_data.data.shape[0]):
        data_processed[i,:,:] = uds3D_data.data[i,r_topLeft:r_bottomRight, c_topLeft:c_bottomRight]
        
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_cp')
    if 'LayerValue(mV)' in uds3D_data.info.keys():
        uds3D_data_processed.info['LayerValue(mV)'] = uds3D_data.info['LayerValue(mV)'].copy()
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
            
    uds3D_data_processed.proc_history.append("ImgProc.ipCropRegion2D:r_topLeft=%d,c_topLeft=%d,r_bottomRight=%d,c_bottomRight=%d" 
                                             % (r_topLeft, c_topLeft, r_bottomRight, c_bottomRight))
    
    return uds3D_data_processed

def ipFourierTransform2D(uds3D_data):
    data_processed = np.zeros_like(uds3D_data.data, dtype=complex)    
    for i in range(uds3D_data.data.shape[0]):
        data_processed[i,:,:] = np.fft.fftshift( np.fft.fft2(uds3D_data.data[i,:,:]) )
        
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_fft')
    uds3D_data_processed.info = uds3D_data.info.copy()
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    uds3D_data_processed.proc_history.append("ImgProc.ipFourierTransform2D:")
    
    return uds3D_data_processed

def ipPerfectLattice(uds3D_data):    
    if uds3D_data.name.split('_')[1] in LatticeType.sampleTolatticeDict.keys():
        lattice = LatticeType.sampleTolatticeDict[uds3D_data.name.split('_')[1]]
        
        bPx1 = uds3D_data.info['BraggPeaks'][0][0]
        bPy1 = uds3D_data.info['BraggPeaks'][0][1]
        bPx2 = uds3D_data.info['BraggPeaks'][1][0]
        bPy2 = uds3D_data.info['BraggPeaks'][1][1]
            
        if lattice == 'SquareLattice':                          
            data_processed = perfectLatticeSqure(uds3D_data.data, bPx1, bPy1, bPx2, bPy2)                
            print("SquareLattice")
        elif lattice == 'HexagonalLattice':
            data_processed = perfectLatticeHexagonal(uds3D_data.data, bPx1, bPy1, bPx2, bPy2)
            print("HexagonalLattice")
        else:
            pass
        
    else:
        data_processed = -1
        print("Sample does not exist")
        
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_pl')
    if 'LayerValue(mV)' in uds3D_data.info.keys():
        uds3D_data_processed.info['LayerValue(mV)'] = uds3D_data.info['LayerValue(mV)'].copy()
    
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    uds3D_data_processed.proc_history.append("ImgProc.ipPerfectLattice:")

    return uds3D_data_processed

def ipCalculateRSigma(uds3D_data, rSigma_ref_a0):
    # calculate pixels of longest lattice constant
    l_lattice_constant_pix = 0
    N = uds3D_data.data.shape[-1]
    O_kx = (N - N%2)/2
    O_ky = (N - N%2)/2
    for i in range(len(uds3D_data.info['BraggPeaks'])):
        bPx = uds3D_data.info['BraggPeaks'][i][0]
        bPy = uds3D_data.info['BraggPeaks'][i][1]
        
        bP = np.sqrt( (bPx-O_kx)**2 + (bPy-O_ky)**2 )
        
        l_lattice_constant_pix = max(l_lattice_constant_pix, N/bP)
    
    # calculate rSigma
    rSigma = rSigma_ref_a0 * l_lattice_constant_pix
    
    return rSigma
    
def ipCalculateDisplacementField(uds3D_data, rSigma_ref_a0):
    bPx1 = uds3D_data.info['BraggPeaks'][0][0]
    bPy1 = uds3D_data.info['BraggPeaks'][0][1]
    bPx2 = uds3D_data.info['BraggPeaks'][1][0]
    bPy2 = uds3D_data.info['BraggPeaks'][1][1]
    
    #
    rSigma = ipCalculateRSigma(uds3D_data, rSigma_ref_a0)
    
    #
    lfc = LFCorrection(uds3D_data.data[0,:,:], bPx1, bPy1, bPx2, bPy2, rSigma)
    
    displacementField = lfc.calculateDisplacementField()
    
    uds3D_data_processed = UdsDataStru3D(displacementField, uds3D_data.name+'_df')
    if 'LayerValue(mV)' in uds3D_data.info.keys():
        uds3D_data_processed.info['LayerValue(mV)'] = uds3D_data.info['LayerValue(mV)'].copy()
    uds3D_data_processed.proc_history.append("ImgProc.ipCalculateDisplacementField:")
    
    return uds3D_data_processed

def ipLFCorrection(uds3D_data, rSigma_ref_a0, displacementField):
    bPx1 = uds3D_data.info['BraggPeaks'][0][0]
    bPy1 = uds3D_data.info['BraggPeaks'][0][1]
    bPx2 = uds3D_data.info['BraggPeaks'][1][0]
    bPy2 = uds3D_data.info['BraggPeaks'][1][1]
    
    #
    rSigma = ipCalculateRSigma(uds3D_data, rSigma_ref_a0)
    print(rSigma)
  
    # Correction
    data_processed = np.zeros_like(uds3D_data.data)
    for i in range(uds3D_data.data.shape[0]):
        lfc = LFCorrection(uds3D_data.data[i,:,:], bPx1, bPy1, bPx2, bPy2, rSigma)    
        lfc.setDisplacementField(displacementField)
        data_processed[i,:,:] = lfc.lFcorrection()
        
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_lf')
    if 'LayerValue(mV)' in uds3D_data.info.keys():
        uds3D_data_processed.info['LayerValue(mV)'] = uds3D_data.info['LayerValue(mV)'].copy()
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    uds3D_data_processed.proc_history.append("ImgProc.ipLFCorrection:")

    return uds3D_data_processed 
    

def ipFourierFilterOut(uds3D_data, windowType="GAUSSIAN", kSigma=1): 
    uds3D_dataCopy = UdsDataStru3D(uds3D_data.data, uds3D_data.name)
    uds3D_dataCopy.info = uds3D_data.info
    
    #
    data_processed = np.copy(uds3D_dataCopy.data)
       
    data_filter_isolated = ipFourierFilterIsolate(uds3D_dataCopy, windowType, kSigma)
    data_processed -= data_filter_isolated.data
    uds3D_dataCopy.data = data_processed
    
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_fo')
    if 'LayerValue(mV)' in uds3D_data.info.keys():
        uds3D_data_processed.info['LayerValue(mV)'] = uds3D_data.info['LayerValue(mV)'].copy()
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    uds3D_data_processed.proc_history.append("ImgProc.ipFourierFilterOut:")
    
    return uds3D_data_processed    
    
def ipFourierFilterIsolate(uds3D_data, windowType="GAUSSIAN", kSigma=1):
    
    uds3D_dataCopy = UdsDataStru3D(uds3D_data.data, uds3D_data.name)
    uds3D_dataCopy.info = uds3D_data.info
    
    #
    data_processed = np.zeros_like(uds3D_dataCopy.data)        
    for i in range(uds3D_dataCopy.data.shape[0]):
        for p in range(len(uds3D_dataCopy.info['FilterPoints'])):
            ftPx = uds3D_dataCopy.info['FilterPoints'][p][0] 
            ftPy = uds3D_dataCopy.info['FilterPoints'][p][1]
            f_filter = FourierFilter(uds3D_dataCopy.data[i,:,:], ftPx, ftPy, windowType, kSigma)
            data_processed[i,:,:] +=  f_filter.fourierFilterIsolate()
            uds3D_dataCopy.data[i,:,:] = uds3D_data.data[i,:,:] - data_processed[i,:,:]
    
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_fi')
    if 'LayerValue(mV)' in uds3D_data.info.keys():
        uds3D_data_processed.info['LayerValue(mV)'] = uds3D_data.info['LayerValue(mV)'].copy()
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    uds3D_data_processed.proc_history.append("ImgProc.ipFourierFilterIsolate:")

    return uds3D_data_processed
    
def ipLockIn2D(uds3D_data, px, py, rSigma_ref_a0, MapType, phaseUnwrap=True,phaseReverseFactor=0.8):
    # calculate pixels of longest lattice constant
    l_lattice_constant_pix = 0
    N = uds3D_data.data.shape[-1]
    O_kx = (N - N%2)/2
    O_ky = (N - N%2)/2
    for i in range(len(uds3D_data.info['BraggPeaks'])):
        bPx = uds3D_data.info['BraggPeaks'][i][0]
        bPy = uds3D_data.info['BraggPeaks'][i][1]
        
        bP = np.sqrt( (bPx-O_kx)**2 + (bPy-O_ky)**2 )
        
        l_lattice_constant_pix = max(l_lattice_constant_pix, N/bP)
    
    # calculate rSigma
    rSigma = rSigma_ref_a0 * l_lattice_constant_pix
    print("rSigma:",rSigma)
    
    # calculate Amplitude or Phase Map 
    data_analysed = np.zeros_like(uds3D_data.data)    
    for i in range(uds3D_data.data.shape[0]):
        lockin = LockIn2D(uds3D_data.data[i,:,:], px, py, rSigma)        
        if MapType == 'Amplitude':
            data_analysed[i,:,:] = lockin.getAmplitudeMap()
        elif MapType == 'Phase':
            data_analysed[i,:,:] = lockin.getPhaseMap(phaseUnwrap, phaseReverseFactor)
        else:
            print("Wrong Type of 2D Lock-in Mapping!")
        
    if MapType == 'Amplitude':
        uds3D_data_analysed = UdsDataStru3D(data_analysed, uds3D_data.name+'_amp')
    elif MapType == 'Phase':
        uds3D_data_analysed = UdsDataStru3D(data_analysed, uds3D_data.name+'_pha')
    if 'LayerValue(mV)' in uds3D_data.info.keys():
        uds3D_data_analysed.info['LayerValue(mV)'] = uds3D_data.info['LayerValue(mV)'].copy()
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_analysed.proc_history.append(i)
    
    uds3D_data_analysed.proc_history.append("ImgProc.ipLockIn2D:")
    
    return uds3D_data_analysed
    
def ipMath(uds3D_data_A, uds3D_data_B, operator="+"):
    data_processed = np.zeros_like(uds3D_data_A.data) 
    
    if operator == "+":
        data_processed =  uds3D_data_A.data + uds3D_data_B.data
    elif operator == "-":
        data_processed =  uds3D_data_A.data - uds3D_data_B.data
    elif operator == "*":
        data_processed =  uds3D_data_A.data * uds3D_data_B.data
    elif operator == "/":
        data_processed =  uds3D_data_A.data / uds3D_data_B.data  
    else:
        print("Unrecogonized operator!")
        
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data_A.name+'_mat'+ operator)
    if 'LayerValue(mV)' in uds3D_data_A.info.keys():
        uds3D_data_processed.info['LayerValue(mV)'] = uds3D_data_A.info['LayerValue(mV)'].copy()
    if len(uds3D_data_A.proc_history) > 0:
        for i in uds3D_data_A.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    uds3D_data_processed.proc_history.append("ImgProc.ipMath:"+operator+uds3D_data_B.name)
    
    return uds3D_data_processed

def ipRmap(uds3D_data):   
    uds_var_layer_value = uds3D_data.info['LayerValue(mV)'].copy()
        
    rMap_layers_value = []
    for i in range(uds3D_data.data.shape[0]):
        if not uds_var_layer_value[i] == 0:
            if - uds_var_layer_value[i] in uds_var_layer_value:
                if not abs(uds_var_layer_value[i]) in rMap_layers_value:
                    rMap_layers_value.append( abs(uds_var_layer_value[i]) )
    
    rMap_layers = len(rMap_layers_value)
    data_processed = np.zeros( (rMap_layers, uds3D_data.data.shape[-2], uds3D_data.data.shape[-1]) )   
    for i in range( rMap_layers ):
        posIdx = uds_var_layer_value.index( rMap_layers_value[i]) 
        negIdx = uds_var_layer_value.index( -rMap_layers_value[i] )
        data_processed[i,:,:] = uds3D_data.data[posIdx,:,:] / uds3D_data.data[negIdx,:,:]
                
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_rmp')
    
    uds3D_data_processed.info['LayerValue(mV)'] = rMap_layers_value.copy()
    
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    uds3D_data_processed.proc_history.append("ImgProc.ipRmap:")
    
    return uds3D_data_processed


def ipGapMap(uds3D_data, order=2, enery_start = 0, enery_end = -1):

    data_processed = GapMap(uds3D_data.data, uds3D_data.info['LayerValue(mV)'], order, enery_start, enery_end)  

    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_gm')
    uds3D_data_processed.info['LayerValue(mV)'] = ['?']
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
            
    uds3D_data_processed.proc_history.append("ImgProc.ipGamMap:order=%d" % (order))
    
    return uds3D_data_processed
        
def ipRegister(uds3D_data):
    data3D = uds3D_data.data
    register_points = uds3D_data.info['RegisterPoints']
    register_points_reference = uds3D_data.info['RegisterReferencePoints']
    
    data_processed = Register(data3D, register_points, register_points_reference)
    
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_rg')
    if 'LayerValue(mV)' in uds3D_data.info.keys():
        uds3D_data_processed.info['LayerValue(mV)'] = uds3D_data.info['LayerValue(mV)'].copy()
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
            
    uds3D_data_processed.proc_history.append("ImgProc.Register: register points: {0}, register reference points: {1}".format(register_points, register_points_reference))
    
    return uds3D_data_processed
    
    