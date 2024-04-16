# -*- coding: utf-8 -*-
"""
Created on Mon Aug 14 22:49:25 2023

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
from .PixelInterpolation import PixelInterpolation  
    
"""
class Module
"""

class AffineTransform():
    def __init__(self):        
        self.A = np.array( [[1.0, 0.0, 0.0],
                            [0.0, 1.0, 0.0],
                            [0.0, 0.0, 1.0]] ) # Affine Matrix, default is Identity Matrix
        
        self.src_X_float = 0
        self.src_Y_float = 0
        
    def setTranslateOfAffineMatrix(self, dx, dy): # dx-column, dy-row
        A_translate = np.array( [[1.0, 0.0,  dx],
                                 [0.0, 1.0,  dy],
                                 [0.0, 0.0, 1.0] ] )
        
        self.A = np.dot( A_translate, self.A)
        
    def setScaleOfAffineMatrix(self, sx, sy): # sx-column, sy-row
        A_scale = np.array( [[ sx, 0.0, 0.0],
                             [0.0,  sy, 0.0],
                             [0.0, 0.0, 1.0] ] )
        
        self.A = np.dot( A_scale, self.A)
        
    def setShearOfAffineMatrix(self, bx, by): # bx-column, by-row
        A_shear = np.array( [[1.0,  bx, 0.0],
                             [ by, 1.0, 0.0],
                             [0.0, 0.0, 1.0] ] )
        
        self.A = np.dot( A_shear, self.A)
        
    def setRotateOfAffineMatrix(self, angle): # angle unit: radian
        c = np.cos(angle)
        s = np.sin(angle)
        A_rotate = np.array( [[  c,  -s, 0.0],
                              [  s,   c, 0.0],
                              [0.0, 0.0, 1.0] ] )
        
        self.A = np.dot( A_rotate, self.A)

    def setAffineMatrixFrom3PairsRpoints(self, rPoints):
        
        src_x0 = rPoints[0][0] #column
        src_y0 = rPoints[0][1] #row
        src_x1 = rPoints[1][0]
        src_y1 = rPoints[1][1]
        src_x2 = rPoints[2][0]
        src_y2 = rPoints[2][1]
        
        tgt_x0 = rPoints[3][0] #column
        tgt_y0 = rPoints[3][1] #row
        tgt_x1 = rPoints[4][0]
        tgt_y1 = rPoints[4][1]
        tgt_x2 = rPoints[5][0]
        tgt_y2 = rPoints[5][1]

        # calclulate Matrix Elements
        d = 1.0 / ( src_x0*(src_y2-src_y1) + src_x1*(src_y0-src_y2) + src_x2*(src_y1-src_y0) )
        
        self.A[0,0] = d * ( src_y0*(tgt_x1-tgt_x2) + src_y1*(tgt_x2-tgt_x0) + src_y2*(tgt_x0-tgt_x1) )
        self.A[0,1] = d * ( src_x0*(tgt_x2-tgt_x1) + src_x1*(tgt_x0-tgt_x2) + src_x2*(tgt_x1-tgt_x0) )
        self.A[1,0] = d * ( src_y0*(tgt_y1-tgt_y2) + src_y1*(tgt_y2-tgt_y0) + src_y2*(tgt_y0-tgt_y1) )
        self.A[1,1] = d * ( src_x0*(tgt_y2-tgt_y1) + src_x1*(tgt_y0-tgt_y2) + src_x2*(tgt_y1-tgt_y0) )
        self.A[0,2] = d * ( src_x0*(src_y2*tgt_x1-src_y1*tgt_x2) +
                            src_x1*(src_y0*tgt_x2-src_y2*tgt_x0) +
                            src_x2*(src_y1*tgt_x0-src_y0*tgt_x1))
        self.A[1,2] = d * ( src_x0*(src_y2*tgt_y1-src_y1*tgt_y2) +
                            src_x1*(src_y0*tgt_y2-src_y2*tgt_y0) +
                            src_x2*(src_y1*tgt_y0-src_y0*tgt_y1))
        
        
    def srcMappedPoints(self, data2D_row, data2D_column):
        src_x = np.arange(data2D_column) #column
        src_y = np.arange(data2D_row) #row
        src_X, src_Y = np.meshgrid(src_x, src_y)
        
        # tgt_r = A * src_r, in Matrix Form
        tgt_X_float = self.A[0][0]*src_X + self.A[0][1]*src_Y + self.A[0][2] * 1
        tgt_Y_float = self.A[1][0]*src_X + self.A[1][1]*src_Y + self.A[1][2] * 1
        
        # get integer (larger) range of target coordinates
        self.tgt_x_min = np.floor(np.amin(tgt_X_float))
        self.tgt_x_max = np.ceil(np.amax(tgt_X_float))
        self.tgt_y_min = np.floor(np.amin(tgt_Y_float))
        self.tgt_y_max = np.ceil(np.amax(tgt_Y_float))
        
        tgt_x = np.arange(self.tgt_x_min, self.tgt_x_max + 1, 1)
        tgt_y = np.arange(self.tgt_y_min, self.tgt_y_max + 1, 1)
        tgt_X, tgt_Y = np.meshgrid(tgt_x, tgt_y)
        
        # calculate inverse of A
        A_inv = np.linalg.inv(self.A)
        
        # calculate coordinates of inverse mapping of target in source
        self.src_X_float = (A_inv[0][0]*tgt_X + A_inv[0][1]*tgt_Y + A_inv[0][2] * 1)
        self.src_Y_float = (A_inv[1][0]*tgt_X + A_inv[1][1]*tgt_Y + A_inv[1][2] * 1)
        
    def affineMapping(self, data2D, interpolate_method='bilinear', pad_method='constant'):
        # transform and interpolation
        px_itp = PixelInterpolation(data2D, self.src_X_float, self.src_Y_float, interpolate_method, pad_method)
        mapped_data = px_itp.dataMapping()

        return mapped_data


    def affineMappingForRegister(self, data2D, interpolate_method='bilinear', pad_method='constant'):
        # transform and interpolation
        px_itp = PixelInterpolation(data2D, self.src_X_float, self.src_Y_float, interpolate_method, pad_method)
        mapped_data = px_itp.dataMapping()
        
        # tgt_x/y_min/max is coordinates; x/y_start/end is array index
        if self.tgt_y_min <= 0:
            y_start = int(0 - self.tgt_y_min)
            y_start_p = 0
            if self.tgt_y_max >= data2D.shape[-2]:
                y_end = int(data2D.shape[-2] - self.tgt_y_min)
                y_end_p = data2D.shape[-2]
            else:
                y_end = int(self.tgt_y_max - self.tgt_y_min)
                y_end_p = int(self.tgt_y_max)
        else:
            y_start = 0
            y_start_p = int(self.tgt_y_min)
            if self.tgt_y_max >= data2D.shape[-2]:
                y_end = int(data2D.shape[-2] - self.tgt_y_min)
                y_end_p = data2D.shape[-2]
            else:
                y_end = int(self.tgt_y_max - self.tgt_y_min) 
                y_end_p = int(self.tgt_y_max) 
        
        
        if self.tgt_x_min <= 0:
            x_start = int(0 - self.tgt_x_min)
            x_start_p = 0
            if self.tgt_x_max >= data2D.shape[-1]:
                x_end = int(data2D.shape[-1] - self.tgt_x_min)
                x_end_p = data2D.shape[-1]
            else:
                x_end = int(self.tgt_x_max - self.tgt_x_min)
                x_end_p = int(self.tgt_x_max)
        else:
            x_start = 0
            x_start_p = int(self.tgt_x_min)
            if self.tgt_x_max >= data2D.shape[-1]:
                x_end = int(data2D.shape[-1] - self.tgt_x_min)
                x_end_p = data2D.shape[-1]
            else:
                x_end = int(self.tgt_x_max - self.tgt_x_min) 
                x_end_p = int(self.tgt_x_max) 
        
        data = np.zeros_like(data2D)
        data[y_start_p : y_end_p, x_start_p : x_end_p] = mapped_data[y_start:y_end, x_start:x_end]
        return data
"""
"""

class ProjectiveTransfrom(): # Four Point Mapping
    
    pass

class BilinearTransform():
    pass

class LogPolarTransfrom():
    pass


    
