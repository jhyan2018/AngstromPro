#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 30 22:27:16 2025

@author: zhaohuiyu
"""

"""
Third-party Modules
"""
import numpy as np
import scipy.io as sio
"""
User Modules
"""
from .UdsDataProcess import UdsDataStru

"""
Class Definition
"""

'''
load npy data into a Data Structure
'''
class DataMatStru():
    
    def __init__(self, path, key=None):
        self.path = path
        self.name = path.split('.')[-2].split('/')[-1]
        self.key = key  # .mat file usually contains multiple variables
    
    def get_mat_data(self):
        mat_dict = sio.loadmat(self.path)
        
        # If no key is specified, use the first valid one
        if self.key is None:
            keys = [k for k in mat_dict.keys() if not k.startswith('__')]
            if len(keys) == 0:
                raise ValueError("No valid data found in .mat file.")
            self.key = keys[0]
        
        data = mat_dict[self.key]
        if data.ndim == 2:
            data = data[np.newaxis, :, :]  # expand to 3D for consistency
        uds_mat = UdsDataStru(data, 'uds3D_' + self.name)
        return uds_mat