'''
Load txt data file into dict named header and a 3D array named data3D.

@author: Ge He
Created on: Sep 22, 2023 

'''

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
load txt data into a Data Structure
'''

## Data structure of 3ds file
class DataTxtStru():
    
    def __init__(self,path):
        self.path = path
        self.name = path.split('.')[-2].split('/')[-1]
    
    # return the number n layer dIdV data
    def get_txt_data(self):
        data = np.loadtxt(self.path, dtype = np.str_, encoding = 'utf-8')
        data = data[:,:].astype(dtype = np.float_)
        data = data[np.newaxis,:,:]
        uds_txt = UdsDataStru3D(data, 'uds3D_'+self.name)
        
        return uds_txt
    
   




        
        