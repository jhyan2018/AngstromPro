# -*- coding: utf-8 -*-
"""
Created on Mon Jul 24 13:54:01 2023

Load STM raw data from *.1FL *.TFR file

@author: Jiahao Yan
"""
"""
Third-party Modules
"""
import numpy as np
"""
User Modules
"""
from .UdsDataProcess import UdsDataStru3D

"""
Class Definition
"""

'''
Load the header and data
'''

class LoadTFR():
    def __init__(self, path):
        self.path = path
        self.header = self.get_header()
        self.data3D = self.load_data()
        
    def get_header(self):
        pass
    
    def load_data(self):
        pass


class Load1FL():
    
    def __init__(self, path):
        self.path = path
        self.header = self.get_header()
        self.data3D = self.load_data()
        
    def get_header(self):
        f = open(self.path, 'rb')
        header = {}
        
        #
        f.seek(406, 0)
        header['xSize']=np.fromfile(f, dtype = np.int32, count = 1 )[0]
        header['ySize']=np.fromfile(f, dtype = np.int32, count = 1 )[0]
        
        f.seek(480, 0)
        header['zSize']=np.fromfile(f, dtype = np.int16, count = 1 )[0]
        
        f.close()
        return header
    
    def load_data(self):
        f = open(self.path, 'rb')
        f.seek(2112, 0)
        
        dataSize = self.header['xSize'] * self.header['ySize'] * self.header['zSize']
        raw_data1D = np.fromfile( f, dtype = np.uint16, count = dataSize )
        data3D = np.reshape(raw_data1D, (self.header['zSize'], self.header['ySize'], self.header['xSize']))
        
        f.close()
        
        return data3D

class Data1FLStru():    
    def __init__(self, path):
        lData = Load1FL(path)
        self.header = lData.header
        self.data3D = lData.data3D
        self.name = path.split('.')[-2].split('/')[-1]
        self.suffix = path.split('.')[-1]
        
    def get_data(self):        
        if self.suffix == '1FL':
            name = 'uds3D_'+self.name+'_dIdV'
        elif self.suffix == 'TFR':
            name = 'uds3D_'+self.name+'_topo'
        else:
            name = 'uds3D_'+self.name+'_unknown'
            
        uds3D_data = UdsDataStru3D(self.data3D, name)
        
        return uds3D_data    
        