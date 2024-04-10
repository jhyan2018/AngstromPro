# -*- coding: utf-8 -*-
'''
Created on Mon Apr  8 13:55:22 2024

@author: Huiyu
'''

'''
System modules
'''
import itertools
'''
Third-party Modules
'''
import numpy as np


    
def GapMap(data3D, LayerValue, order=2):
    '''' data shoud only have 2 axis/dimensions'''
    
    ''' least square fitting'''
    '''
    fitting curve/surface:
        z = b + k1 x + k2 x^2 + k3 x^3 + ...
            
    To get the best fittings for unkonwn parameters k1, k2, k3 ... can be sovled in matrix form,
    and all the points of (x_i, z_i) are known. 
    
    In the matrix form:
    A p = q, A is a matrix, p and q are vectors
    
    A = (1->, x_>, x^2_>, x^3_>, ... ),  x_> is a vector inlcuding all the known points on energy axis
    p = (b, k1, k2, k3, ...)^T, T means transpose
    q = z_> , z_> is a vector including all the dI/dV value of all corresponding known points for fitting
    
    When z is maxmum, z' = 0 & z'' < 0 (z'/z'' is the derivative/second derivative of z)
    
    '''
    
    energy = np.array(LayerValue)
    energy_points = energy.shape[0]
    X_points = data3D.shape[-2] # real space x axis
    Y_points = data3D.shape[-1] # real space y axis
    
    A_matrix_columns = order + 1 # 1: Constant term
    A_matrix = np.zeros((energy_points, A_matrix_columns)) #Fit the relationship between energy and dIdV of each space point
    
    gapmap = np.zeros((X_points, Y_points))
    
    item_order = itertools.product(range(X_points), range(Y_points))
    for k, (X,Y) in enumerate(item_order): # iterate each space point
        
        dIdV = data3D[:,X,Y]
        
        # Determine the matrix A
        for i in range(A_matrix_columns):
            A_matrix[:,i] = energy**i
                        
        p,res,_,_ = np.linalg.lstsq(A_matrix, dIdV, rcond=None)
        dIdV_Fitted = np.poly1d(p[::-1])
        dIdV_derivative = np.polyder(dIdV_Fitted, 1)
        dIdV_second_order_dervative = np.polyder(dIdV_Fitted, 2)
        roots = dIdV_derivative.r
        for i in range(len(roots)):
            if (dIdV_second_order_dervative(roots[i]) < 0) & (roots[i] > np.min(energy)) & (roots[i] < np.max(energy)):
                gapmap[X,Y] = roots[i]
                
    gapmap = gapmap[np.newaxis,:,:]
        
    return gapmap
    
     
    
    
    