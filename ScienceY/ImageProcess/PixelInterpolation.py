# -*- coding: utf-8 -*-
"""
Created on Mon Aug 14 22:55:41 2023

@author: Jiahao Yan & Huiyu Zhao
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


class PixelInterpolation():
    def __init__(self, src_data2D, src_X_f, src_Y_f, interpolate_method='bilinear', pad_method='constant'):
        self.src_data = src_data2D
        self.src_X_f = src_X_f
        self.src_Y_f = src_Y_f
        self.interpolate_method = interpolate_method
        self.pad_method = pad_method
        
        self.src_data_padded = 0       
        self.offset_x = 0
        self.offset_y = 0
        
        self.dataPadding()
    
    def dataPadding(self):
        """ padding """
        # calculate the padding size for data
        data_size_max = max(self.src_data.shape[-1], self.src_data.shape[-2])
        padding_size = int((data_size_max - data_size_max%2)/2)
        
        # make sure the affine mapped XY region in src data 
        # won't exceed the padding region which is twice as the original src data
        src_X_f_max = np.ceil(np.amax(self.src_X_f))
        src_X_f_min = np.floor(np.amin(self.src_X_f))
        src_Y_f_max = np.ceil(np.amax(self.src_Y_f))
        src_Y_f_min = np.floor(np.amin(self.src_Y_f))
        
        src_XY_border_max = int( max( 0 - src_X_f_min, 0 - src_Y_f_min,
                                src_X_f_max - self.src_data.shape[-1] + 1,
                                src_Y_f_max - self.src_data.shape[-2] + 1) )
        
        if src_XY_border_max > 0:
            padding_size += src_XY_border_max
            
        self.offset_x = padding_size
        self.offset_y = padding_size
        
        # pad src data
        self.src_data_padded = np.lib.pad(self.src_data, (padding_size, padding_size), self.pad_method, constant_values = 0)
    
    def dataMapping(self):
        tgt_data = np.zeros_like(self.src_X_f)
            
        for i in range(self.src_X_f.shape[-2]):
            for j in range(self.src_X_f.shape[-1]):
                tgt_data[i,j] = self.interpolate(self.src_Y_f[i,j]+self.offset_y, 
                                                   self.src_X_f[i,j]+self.offset_x)
        
        return tgt_data      
        
    def interpolate(self, offset_y_f, offset_x_f):
        if self.interpolate_method == 'bilinear':
            return self.bilinearInterpolate(offset_y_f, offset_x_f)
        elif self.interpolate_method == 'bicubic':
            pass
        else:
            pass
        pass
          
    def bilinearInterpolate(self, offset_y_f, offset_x_f):
        u_x = int(np.floor(offset_x_f))
        v_y = int(np.floor(offset_y_f))
        
        a_x = offset_x_f - u_x
        b_y = offset_y_f - v_y
        
        interplated_data = (a_x-1)*(b_y-1)*self.src_data_padded[v_y, u_x]
        interplated_data += a_x*(1-b_y)*self.src_data_padded[v_y, u_x+1]
        interplated_data += (1-a_x)*b_y*self.src_data_padded[v_y+1, u_x]
        interplated_data += a_x*b_y*self.src_data_padded[v_y+1, u_x+1]
                            
        return interplated_data
    def bicubicInterploate(self, offset_y_f, offset_x_f):
        pass
    
class RasterPixelInterpolation():
    def __init__(self, src_data2D, src_X_f, src_Y_f, interpolate_method='bilinear'):
        self.src_data = src_data2D
        self.src_X_f = src_X_f
        self.src_Y_f = src_Y_f
        self.interpolate_method = interpolate_method
    
    def interpolate(self, MODULUS=False):
        if self.interpolate_method == 'bilinear':
            return self.bilinearInterpolate(MODULUS)
        else:
            pass
          
    def bilinearInterpolate(self, MODULUS):
        interplated_data = np.zeros((1,len(self.src_X_f)))

        for i in range(len(self.src_X_f)):
            u_x = int(np.floor(self.src_X_f[i]))
            v_y = int(np.floor(self.src_Y_f[i]))
        
            a_x = self.src_X_f[i] - u_x
            b_y = self.src_Y_f[i] - v_y
            
            if MODULUS:
                interplated_data[0,i] = (a_x-1)*(b_y-1)*abs(self.src_data[v_y, u_x])
                interplated_data[0,i] += a_x*(1-b_y)*abs(self.src_data[v_y, u_x+1])
                interplated_data[0,i] += (1-a_x)*b_y*abs(self.src_data[v_y+1, u_x])
                interplated_data[0,i] += a_x*b_y*abs(self.src_data[v_y+1, u_x+1])
            else:
                interplated_data[0,i] = (a_x-1)*(b_y-1)*self.src_data[v_y, u_x]
                interplated_data[0,i] += a_x*(1-b_y)*self.src_data[v_y, u_x+1]
                interplated_data[0,i] += (1-a_x)*b_y*self.src_data[v_y+1, u_x]
                interplated_data[0,i] += a_x*b_y*self.src_data[v_y+1, u_x+1]
            
        return interplated_data