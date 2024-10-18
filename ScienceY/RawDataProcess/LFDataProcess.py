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
from .UdsDataProcess import UdsDataStru
from ..GUI.general.NumberExpression import NumberExpression

"""
Class Definition
"""

'''
Load the header and data
'''

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
        
        f.seek(1024 + 22, 0)
        header['Bias (V)']=np.fromfile(f, dtype = np.float32, count = 1 )[0] * 1e-3
        header['Current Setpoint (A)']=np.fromfile(f, dtype = np.float32, count = 1 )[0] * 1e-9

        f.seek(1024 + 34, 0)
        header['Scan Range (m)']=np.fromfile(f, dtype = np.float32, count = 1 )[0] * 1e-10
        
        f.seek(1280, 0)
        header['sweep start (V)']=np.fromfile(f, dtype = np.float32, count = 1 )[0]
        header['sweep stop (V)']=np.fromfile(f, dtype = np.float32, count = 1 )[0]
        
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
        
    def setDataInfo(self, uds_data):
        info = uds_data.info
        
        info['Current Setpoint(A)'] = str(self.header['Current Setpoint (A)'])
        info['Bias (V)'] = str(self.header['Bias (V)'])
        
        if self.suffix == '1FL':
            info['LayerSignal'] = 'Bias (V)'
            layer_value_list = []
            for a_v in uds_data.axis_value[0]:
                layer_value_list.append(NumberExpression.float_to_simplified_number(a_v))
            separator = ',' 
            info['LayerValue'] = separator.join(layer_value_list)
        elif self.suffix == 'TFR':
            info['LayerValue'] = str(self.header['Bias (V)'])            
        else:
            pass
        
        # info - channel
        if self.suffix == '1FL':
            info['Channel'] = 'dI/dV Map'
            info['Data_Name_Unit'] = 'dI/dV (S)'
        elif self.suffix == 'TFR':
            info['Channel'] = 'Topo'
            info['Data_Name_Unit'] = 'Z (m)'
        else:
            pass
    
    def extractData(self):
        if self.suffix == '1FL':
            name = 'uds3D_'+self.name+'_dIdV'
        elif self.suffix == 'TFR':
            name = 'uds3D_'+self.name+'_topo'
        else:
            name = 'uds3D_'+self.name+'_unknown'
            
        uds_data = UdsDataStru(self.data3D, name)
        
        # axis name
        uds_data.axis_name = ['Bias (V)', 'X (m)', 'Y (m)']
        
        # axis value
        if self.suffix == '1FL':
            vStart = self.header['sweep start (V)']
            vStop = self.header['sweep stop (V)']
            vPoints = self.header['zSize']
            vv = np.linspace(vStart, vStop, vPoints)
            uds_data.axis_value.append(vv.tolist())
        elif self.suffix == 'TFR':
            uds_data.axis_value.append([self.header['Bias (V)']])
        else:
            print('Unknow file type for STM1&2!') 

        x_width = self.header['Scan Range (m)']
        y_height = self.header['Scan Range (m)']
        x_points = self.header['xSize']
        y_points = self.header['ySize']
            
        xx = np.linspace(0,x_width, x_points)
        yy = np.linspace(0,y_height, y_points)
        uds_data.axis_value.append(xx.tolist())
        uds_data.axis_value.append(yy.tolist())
        
        # info
        self.setDataInfo(uds_data)
        
        return uds_data
    
    def get_dIdV(self):
        uds_dIdV = self.extractData()
        
        return uds_dIdV
    
    def get_Topo(self):
        uds_Topo = self.extractData()
        
        return uds_Topo  
        