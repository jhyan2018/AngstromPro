# -*- coding: utf-8 -*-
"""
Created on Sun Aug 13 18:19:39 2023

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
from ..RawDataProcess.UdsDataProcess import UdsDataStru3D
from ..GUI.general.NumberExpression import NumberExpression

from .BackgroundSubtract import backgroundSubtract2DPlane, backgroundSubtractPerLine
from .PerfectLattice import perfectLatticeSqure, perfectLatticeHexagonal
from .FourierFilter import FourierFilter
from .LockIn2D import LockIn2D
from .LFCorrection import LFCorrection
from .GapMap import GapMap
from .Register import Register
from . StatisticCrossCorrelation import StatisticCrossCorrelation
from . CrossCorrelation import CrossCorrelation
"""
function Module
"""
def ipCopyDataInfo(data_info):
    copied_info = data_info.copy()    
    copied_info.pop('BraggPeaks', None)

    return copied_info

def ipGetLayerValue(uds_data, isSnTxt=False):
    layer_value = []
    if 'LayerValue' in uds_data.info:
        layer_value_txt = uds_data.info['LayerValue'].split(',')
        for v in layer_value_txt:                    
            if isSnTxt:
                layer_value.append(v)
            else:
                v_text = NumberExpression.simplified_number_to_float(v)
                layer_value.append(v_text)
    return layer_value

def ipGetPickedPoints(uds_data, info_key):
    if info_key in uds_data.info:
        Points_text = uds_data.info[info_key].split(',')
        Points=[]
        for p in Points_text:
            Points.append( int(p) )
        Points_array = np.array(Points)
        
        pn = int(len(Points_array)/2)
        Points_array = Points_array.reshape(pn, 2)
    else:
        print('No - ', info_key,' - keys exist!')
        Points_array = np.array([])
    
    return Points_array

def ipBackgroundSubtract2D(uds3D_data, order=1, method='2DPlane'):
    data_processed = np.zeros_like(uds3D_data.data)
    for i in range(uds3D_data.data.shape[0]):
        if method == '2DPlane':
            data_processed[i,:,:] = backgroundSubtract2DPlane(uds3D_data.data[i,:,:], order)
        elif method == 'PerLine':
            data_processed[i,:,:] = backgroundSubtractPerLine(uds3D_data.data[i,:,:], order)  

    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_bg')

    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data.info)
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
            
    #
    c_history = 'ImgProc.ipBackgroundSubtract2D:'
    c_history += 'order=' + str(order) + ';'
    c_history += 'method=' + method
    uds3D_data_processed.proc_history.append(c_history)
    
    return uds3D_data_processed

def ipCropRegion2D(uds3D_data, r_topLeft, c_topLeft, r_bottomRight, c_bottomRight):
    r_side_len = r_bottomRight - r_topLeft + 1
    c_side_len = c_bottomRight - c_topLeft + 1
    
    data_processed = np.zeros((uds3D_data.data.shape[0], r_side_len, c_side_len))
    for i in range(uds3D_data.data.shape[0]):
        data_processed[i,:,:] = uds3D_data.data[i,r_topLeft:r_bottomRight+1, c_topLeft:c_bottomRight+1]
        
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_cp')
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data.info)
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    #
    c_history = 'ImgProc.ipCropRegion2D:'   
    c_history += 'r_topLeft=' + str(r_topLeft) + ';'
    c_history += 'c_topLeft=' + str(c_topLeft) + ';'
    c_history += 'r_bottomRight=' + str(r_bottomRight) + ';'
    c_history += 'c_bottomRight=' + str(c_bottomRight)
    uds3D_data_processed.proc_history.append(c_history)
    
    return uds3D_data_processed

def ipFourierTransform2D(uds3D_data):
    data_processed = np.zeros_like(uds3D_data.data, dtype=complex)    
    for i in range(uds3D_data.data.shape[0]):
        data_processed[i,:,:] = np.fft.fftshift( np.fft.fft2(uds3D_data.data[i,:,:]) )
        
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_fft')
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data.info)
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    #
    c_history = 'ImgProc.ipFourierTransform2D:'
    uds3D_data_processed.proc_history.append(c_history)
    
    return uds3D_data_processed

def ipPerfectLattice(uds3D_data, lattice_type):     
    BraggPeaks = ipGetPickedPoints(uds3D_data, 'BraggPeaks')
    
    if len(BraggPeaks) == 0:
        uds3D_data_err = UdsDataStru3D(np.zeros_like(uds3D_data.data), uds3D_data.name+'_err') 
        uds3D_data_err.info = ipCopyDataInfo(uds3D_data.info)
        return uds3D_data_err
    
    bPx1 = BraggPeaks[0][0]
    bPy1 = BraggPeaks[0][1]
    bPx2 = BraggPeaks[1][0]
    bPy2 = BraggPeaks[1][1]
            
    if lattice_type == 'SquareLattice':                          
        data_processed = perfectLatticeSqure(uds3D_data.data, bPx1, bPy1, bPx2, bPy2)                
        print("SquareLattice")
    elif lattice_type == 'HexagonalLattice':
        data_processed = perfectLatticeHexagonal(uds3D_data.data, bPx1, bPy1, bPx2, bPy2)
        print("HexagonalLattice")
    else:
        data_processed = np.zeros((uds3D_data.data[-2], uds3D_data.data[-1]))
        print("Lattice type does not exist!")
        
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_pl')
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data.info)
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    #
    c_history = 'ImgProc.ipPerfectLattice:'
    c_history += 'lattice_type=' + lattice_type + ';'
    c_history += 'BraggPeaks=' + uds3D_data.info['BraggPeaks']
    uds3D_data_processed.proc_history.append(c_history)

    return uds3D_data_processed

def ipCalculateRSigma(uds3D_data, rSigma_ref_a0):
    # calculate pixels of longest lattice constant
    l_lattice_constant_pix = 0
    N = uds3D_data.data.shape[-1]
    O_kx = (N - N%2)/2
    O_ky = (N - N%2)/2
    
    BraggPeaks = ipGetPickedPoints(uds3D_data, 'BraggPeaks')
    
    for i in range(BraggPeaks.shape[0]):
        bPx = BraggPeaks[i][0]
        bPy = BraggPeaks[i][1]
        
        bP = np.sqrt( (bPx-O_kx)**2 + (bPy-O_ky)**2 )
        
        l_lattice_constant_pix = max(l_lattice_constant_pix, N/bP)
    
    # calculate rSigma
    rSigma = rSigma_ref_a0 * l_lattice_constant_pix
    
    return rSigma
    
def ipCalculateDisplacementField(uds3D_data, rSigma_ref_a0):
    BraggPeaks = ipGetPickedPoints(uds3D_data, 'BraggPeaks')
    if len(BraggPeaks) == 0:
        uds3D_data_err = UdsDataStru3D(np.zeros_like(uds3D_data.data), uds3D_data.name+'_df') 
        uds3D_data_err.info = ipCopyDataInfo(uds3D_data.info)
        return uds3D_data_err
    
    bPx1 = BraggPeaks[0][0]
    bPy1 = BraggPeaks[0][1]
    bPx2 = BraggPeaks[1][0]
    bPy2 = BraggPeaks[1][1]
    
    #
    rSigma = ipCalculateRSigma(uds3D_data, rSigma_ref_a0)
    
    #
    lfc = LFCorrection(uds3D_data.data[0,:,:], bPx1, bPy1, bPx2, bPy2, rSigma)
    
    displacementField = lfc.calculateDisplacementField()
    
    uds3D_data_processed = UdsDataStru3D(displacementField, uds3D_data.name+'_df')
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data.info)
    
    uds3D_data_processed.info['LayerValue'] = '0,1'
    
    #
    c_history = 'ImgProc.ipCalculateDisplacementField:'
    c_history += 'rSigma_ref_a0=' + str(rSigma_ref_a0) + ';'
    c_history += 'BraggPeaks=' + uds3D_data.info['BraggPeaks']
    uds3D_data_processed.proc_history.append(c_history)
    
    return uds3D_data_processed

def ipLFCorrection(uds3D_data, rSigma_ref_a0, displacementField):
    BraggPeaks = ipGetPickedPoints(uds3D_data, 'BraggPeaks')
    
    if len(BraggPeaks) == 0:
        uds3D_data_err = UdsDataStru3D(np.zeros_like(uds3D_data.data), uds3D_data.name+'_err') 
        uds3D_data_err.info = ipCopyDataInfo(uds3D_data.info)
        return uds3D_data_err
    
    bPx1 = BraggPeaks[0][0]
    bPy1 = BraggPeaks[0][1]
    bPx2 = BraggPeaks[1][0]
    bPy2 = BraggPeaks[1][1]
    
    #
    rSigma = ipCalculateRSigma(uds3D_data, rSigma_ref_a0)
  
    # Correction
    data_processed = np.zeros_like(uds3D_data.data)
    for i in range(uds3D_data.data.shape[0]):
        lfc = LFCorrection(uds3D_data.data[i,:,:], bPx1, bPy1, bPx2, bPy2, rSigma)    
        lfc.setDisplacementField(displacementField.data)
        data_processed[i,:,:] = lfc.lFcorrection()
        
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_lf')
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data.info)
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    #
    c_history ='ImgProc.ipLFCorrection:'
    c_history += 'rSigma_ref_a0=' + str(rSigma_ref_a0) + ';'
    c_history += 'displacementField=' + displacementField.name + ';'
    c_history += 'BraggPeaks=' + uds3D_data.info['BraggPeaks']
    uds3D_data_processed.proc_history.append(c_history)

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
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data.info)
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    #
    c_history ='ImgProc.ipFourierFilterOut:'
    c_history += 'windowType=' + windowType + ';'
    c_history += 'kSigma=' + str(kSigma) + ';'
    c_history += 'FilterPoints=' + uds3D_data.info['FilterPoints']
    uds3D_data_processed.proc_history.append(c_history)
    
    return uds3D_data_processed    
    
def ipFourierFilterIsolate(uds3D_data, windowType="GAUSSIAN", kSigma=1):
    
    uds3D_dataCopy = UdsDataStru3D(uds3D_data.data, uds3D_data.name)
    uds3D_dataCopy.info = uds3D_data.info
    
    #
    data_processed = np.zeros_like(uds3D_dataCopy.data)        
    
    FilterPoints = ipGetPickedPoints(uds3D_dataCopy, 'FilterPoints')
    if len(FilterPoints) == 0:
        uds3D_data_err = UdsDataStru3D(np.zeros_like(uds3D_data.data), uds3D_data.name+'_err') 
        uds3D_data_err.info = ipCopyDataInfo(uds3D_data.info)
        return uds3D_data_err
    
    for i in range(uds3D_dataCopy.data.shape[0]):
        for p in  range(FilterPoints.shape[0]):
            ftPx = FilterPoints[p][0] 
            ftPy = FilterPoints[p][1]
            f_filter = FourierFilter(uds3D_dataCopy.data[i,:,:], ftPx, ftPy, windowType, kSigma)
            data_processed[i,:,:] +=  f_filter.fourierFilterIsolate()
            uds3D_dataCopy.data[i,:,:] = uds3D_data.data[i,:,:] - data_processed[i,:,:]
    
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_fi')
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data.info)
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    #
    c_history ='ImgProc.ipFourierFilterIsolate:'
    c_history += 'windowType=' + windowType + ';'
    c_history += 'kSigma=' + str(kSigma) + ';'
    c_history += 'FilterPoints=' + uds3D_data.info['FilterPoints']
    uds3D_data_processed.proc_history.append(c_history)

    return uds3D_data_processed
    
def ipLockIn2D(uds3D_data, px, py, rSigma_ref_a0, MapType, phaseUnwrap=True,phaseReverseFactor=0.8):
    # calculate pixels of longest lattice constant
    l_lattice_constant_pix = 0
    N = uds3D_data.data.shape[-1]
    O_kx = (N - N%2)/2
    O_ky = (N - N%2)/2
    
    BraggPeaks = ipGetPickedPoints(uds3D_data, 'BraggPeaks')
    if len(BraggPeaks) == 0:
        uds3D_data_err = UdsDataStru3D(np.zeros_like(uds3D_data.data), uds3D_data.name+'_err') 
        uds3D_data_err.info = ipCopyDataInfo(uds3D_data.info)
        return uds3D_data_err
    
    for i in range(BraggPeaks.shape[0]):
        bPx = BraggPeaks[i][0]
        bPy = BraggPeaks[i][1]
        
        bP = np.sqrt( (bPx-O_kx)**2 + (bPy-O_ky)**2 )
        
        l_lattice_constant_pix = max(l_lattice_constant_pix, N/bP)
    
    # calculate rSigma
    rSigma = rSigma_ref_a0 * l_lattice_constant_pix
    #print("rSigma:",rSigma)
    
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
    
    uds3D_data_analysed.info = ipCopyDataInfo(uds3D_data.info)
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_analysed.proc_history.append(i)
    
    #
    c_history ='ImgProc.ipLockIn2D:'
    c_history += 'px=' + str(px) + ';'
    c_history += 'py=' + str(py) + ';'
    c_history += 'rSigma_ref_a0=' + str(rSigma_ref_a0) + ';'
    c_history += 'MapType=' + MapType + ';'
    c_history += 'phaseUnwrap=' + str(phaseUnwrap) + ';'
    c_history += 'phaseReverseFactor=' + str(phaseReverseFactor) + ';'
    c_history += 'BraggPeaks=' + uds3D_data.info['BraggPeaks']
    uds3D_data_analysed.proc_history.append(c_history)
    
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
        
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data_A.name+'_mat')
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data_A.info)
    if len(uds3D_data_A.proc_history) > 0:
        for i in uds3D_data_A.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    #
    c_history ='ImgProc.ipMath:'
    c_history += 'operator=' + operator + ';'
    c_history += 'uds3D_data_B=' + uds3D_data_B.name     
    uds3D_data_processed.proc_history.append(c_history)
    
    return uds3D_data_processed

def ipRmap(uds3D_data):
    uds_var_layer_value = ipGetLayerValue(uds3D_data, False)
        
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
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data.info)
    rMap_layers_value_text = []
    for v  in rMap_layers_value:
        v_text = NumberExpression.float_to_simplified_number(v)
        rMap_layers_value_text.append(v_text)
    separator = ','
    uds3D_data_processed.info['LayerValue'] = separator.join(rMap_layers_value_text)
    
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    #
    c_history ='ImgProc.ipRmap:'
    uds3D_data_processed.proc_history.append(c_history)
    
    return uds3D_data_processed


def ipGapMap(uds3D_data, order=2, enery_start = 0, enery_end = -1):
    layer_value = ipGetLayerValue(uds3D_data)
    if len(layer_value) == 0:
        uds3D_data_err = UdsDataStru3D(np.zeros_like(uds3D_data.data), uds3D_data.name+'_err') 
        uds3D_data_err.info = ipCopyDataInfo(uds3D_data.info)
        return uds3D_data_err

    data_processed = GapMap(uds3D_data.data, layer_value, order, enery_start, enery_end)  

    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_gm')
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data.info)

    uds3D_data_processed.info['LayerValue'] = '0'
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    #
    c_history ='ImgProc.ipGapMap:'
    c_history += 'order=' + str(order) + ';'
    c_history += 'enery_start=' + str(enery_start) + ';'
    c_history += 'enery_end=' + str(enery_end)
    uds3D_data_processed.proc_history.append(c_history)
    
    return uds3D_data_processed
        
def ipRegister(uds3D_data):
    data3D = uds3D_data.data
    register_points = ipGetPickedPoints(uds3D_data, 'RegisterPoints')
    if len(register_points) == 0:
        uds3D_data_err = UdsDataStru3D(np.zeros_like(uds3D_data.data), uds3D_data.name+'_err') 
        uds3D_data_err.info = ipCopyDataInfo(uds3D_data.info)
        return uds3D_data_err
    
    register_points_reference =  ipGetPickedPoints(uds3D_data, 'RegisterReferencePoints')
    if len(register_points_reference) == 0:
        uds3D_data_err = UdsDataStru3D(np.zeros_like(uds3D_data.data), uds3D_data.name+'_err') 
        uds3D_data_err.info = ipCopyDataInfo(uds3D_data.info)
        return uds3D_data_err
    
    data_processed = Register(data3D, register_points, register_points_reference)
    
    uds3D_data_processed = UdsDataStru3D(data_processed, uds3D_data.name+'_rg')
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data.info)
    if len(uds3D_data.proc_history) > 0:
        for i in uds3D_data.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    #
    c_history ='ImgProc.ipRegister:'
    c_history += 'RegisterPoints=' + uds3D_data.info['RegisterPoints'] + ';'
    c_history += 'RegisterReferencePoints=' + uds3D_data.info['RegisterReferencePoints']
    uds3D_data_processed.proc_history.append(c_history)
    
    return uds3D_data_processed

def ipStatisticCrossCorrelation(uds3D_data1, uds3D_data2,size = 100, sigma = 3):
    data2Da = uds3D_data1.data[0,:,:]
    data2Db = uds3D_data2.data[0,:,:]
    data_processed = StatisticCrossCorrelation(data2Da, data2Db, size, sigma)
    
    uds3D_data_processed = UdsDataStru3D(data_processed[np.newaxis,:,:], uds3D_data1.name+'_sxcorr')
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data1.info)
    if len(uds3D_data1.proc_history) > 0:
        for i in uds3D_data1.proc_history:
            uds3D_data_processed.proc_history.append(i)
            
    #
    c_history ='ImgProc.ipStatisticCrossCorrelation:'
    c_history += 'uds3D_data2=' + uds3D_data2.name + ';' 
    c_history += 'size=' + str(size) + ';'
    c_history += 'sigma=' + str(sigma)
    uds3D_data_processed.proc_history.append(c_history)
    
    return uds3D_data_processed

def ipCrossCorrelation(uds3D_data1, uds3D_data2):
    data2Da = uds3D_data1.data[0,:,:]
    data2Db = uds3D_data2.data[0,:,:]
    data_processed = CrossCorrelation(data2Da, data2Db)
    
    uds3D_data_processed = UdsDataStru3D(data_processed[np.newaxis,:,:], uds3D_data1.name+'_xcorr')
    
    uds3D_data_processed.info = ipCopyDataInfo(uds3D_data1.info)
    if len(uds3D_data1.proc_history) > 0:
        for i in uds3D_data1.proc_history:
            uds3D_data_processed.proc_history.append(i)
            
    #
    c_history ='ImgProc.ipCrossCorrelation:'
    c_history += 'uds3D_data2=' + uds3D_data2.name
    uds3D_data_processed.proc_history.append(c_history)
    
    return uds3D_data_processed
    