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
        self.info = dict()
        self.proc_history = []
        self.proc_to_do = []
        
class UdsDataStru1D(): 
       
     def __init__(self,data1D,name):        
         self.data = np.copy(data1D)
         self.name = name
         self.info = dict()   
        