# -*- coding: utf-8 -*-
"""
Created on Mon Jul 24 14:47:18 2023

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

"""
function Module
"""

class UdsDataStru3D():

    def __init__(self,data3D,name):        
        self.data = np.copy(data3D)
        self.name = name
        self.info = []
        self.proc_history = []
        self.proc_to_do = []

class UdsDataStru2D(): 
       
     def __init__(self,data2D,name):        
         self.data = np.copy(data2D)
         self.name = name
         self.info = []
         self.proc_history = []
         self.proc_to_do = []
        
class UdsDataStru1D(): 
       
     def __init__(self,data1D,name):        
         self.data = np.copy(data1D)
         self.name = name
         self.info = []
         self.proc_history = []
         self.proc_to_do = []
         
class UdsDataProcess():
    def __init__(self, path, uds_data):
        self.path = path
        self.uds_data = uds_data
        self.uds_type = self.uds_data.name[0:5]
        
    def saveToFile(self):
        if self.uds_type == 'uds1D':
            pass
        
        elif self.uds_type == 'uds2D':
            pass
        
        elif self.uds_type == 'uds3D':
            self.saveHead()
            self.saveData()        
        else:
            pass
    
    def readFromFile(self):
        pass
    
    def saveHead(self):
        f = open(self.path, 'wb')
        
        name = self.uds_data.name+'\n'
        f.write(name.encode('utf-8'))
        
        #
        info = []
        if len(self.uds_data.info) > 0:
            for i in self.uds_data.info:
                info.append((i + '\n').encode('utf-8'))
            f.writelines(info)            
        f.write(':INFO_END:\n'.encode('utf-8'))
        
        proc_history = []
        if len(self.uds_data.proc_history) > 0:
            for history in self.uds_data.proc_history:
                proc_history.append((history + '\n').encode('utf-8'))
            f.writelines(proc_history)
        f.write(':PROC_HISTORY_END:\n'.encode('utf-8'))
        
        proc_to_do = []
        if len(self.uds_data.proc_to_do) > 0:
            for to_do in self.uds_data.proc_to_do:
                proc_to_do.append((to_do + '\n').encode('utf-8'))
            f.writelines(proc_to_do)
        f.write(':HEADER_END:\n'.encode('utf-8'))        
        
        
        f.close()
    
    def saveData(self):
        pass

        