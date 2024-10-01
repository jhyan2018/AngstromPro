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
from ..RawDataProcess.UdsDataProcess import UdsDataStru

"""
function Module
"""


def CustomizedAlgorithm(uds3D_data_A, uds3D_data_B, parameters):

    return np.zeros_like(uds3D_data_A.data)


""" DO NOT MODIFY THE CODE BELOW"""
def IPC(uds3D_data_A, uds3D_data_B, parameters):
          
    data_processed = CustomizedAlgorithm(uds3D_data_A, uds3D_data_B, parameters) 
   
    uds3D_data_processed = UdsDataStru(data_processed, uds3D_data_A.name+'_ipc')
    
    uds3D_data_processed.info = uds3D_data_A.info.copy()
    
    if len(uds3D_data_A.proc_history) > 0:
        for i in uds3D_data_A.proc_history:
            uds3D_data_processed.proc_history.append(i)
    
    uds3D_data_processed.proc_history.append("ImgProcCustomized.IPC:")
    
    return uds3D_data_processed

    