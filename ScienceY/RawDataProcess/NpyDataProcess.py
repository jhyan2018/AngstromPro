#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 30 15:39:04 2025

@author: zhaohuiyu
"""


"""
Third-party Modules
"""
import numpy as np
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

## Data structure of 3ds file
class DataNpyStru():
    
    def __init__(self,path):
        self.path = path
        self.name = path.split('.')[-2].split('/')[-1]
    
    # return the number n layer dIdV data
    def get_npy_data(self):
        data = np.load(self.path)   # 直接加载 numpy 数组
        if data.ndim == 2:
            data = data[np.newaxis, :, :]  # 保持与 txt 一致的 3D 结构
        uds_npy = UdsDataStru(data, 'uds3D_' + self.name)
        return uds_npy
    