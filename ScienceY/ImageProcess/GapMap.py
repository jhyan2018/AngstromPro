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


    
def GapMap(data3D, LayerValue, order=2, energy_start = 0, energy_end = -1):
    '''
    Parameters 
	---------- 
	data3D : Three-dimensional dI/dV data 
    LayerValue : Bias for each layer in data3D
	order : int 
        2: Fitting superconducting coherence peaks using second-order polynomials
        3: Fitting superconducting coherence peaks using third-order polynomials
	        ...... 
	        The default is 2. 
    energy_start: Fitting starts from the 'energy_start'th layer of energy
    energy_end: Fitting ends on the 'energy_end'th layer of energy
    returns the energy of the superconducting coherence peaks on each space point.
    ----------
    least square fitting
    
    fitting curve/surface:
        z = b + k1 x + k2 x^2 + k3 x^3 + ...
            
    To get the best fittings for unkonwn parameters k1, k2, k3 ... can be sovled in matrix form,
    and all the points of (x_i, z_i) are known. 
    
    In the matrix form:
    A p = q, A is a matrix, p and q are vectors
    
    A = (1_>, x_>, x^2_>, x^3_>, ... ),  x_> is a vector inlcuding all the known points on energy axis
    p = (b, k1, k2, k3, ...)^T, T means transpose
    q = z_> , z_> is a vector including all the dI/dV value of all corresponding known points for fitting
    
    When z is maxmum, z' = 0 & z'' < 0 (z'/z'' is the derivative/second derivative of z)
    
    '''
    if energy_end != -1:
        energy = np.array(LayerValue)[energy_start:energy_end+1]
    else:
        energy = np.array(LayerValue)
    
    energy_points = energy.shape[0]
    X_points = data3D.shape[-2] # real space x axis
    Y_points = data3D.shape[-1] # real space y axis
    
    A_matrix_columns = order + 1 # 1: Constant term
    A_matrix = np.zeros((energy_points, A_matrix_columns)) #Fit the relationship between energy and dIdV of each space point
    for i in range(A_matrix_columns):
        A_matrix[:, i] = energy ** i
    
    gapmap = np.zeros((X_points, Y_points))
    R2map = np.zeros((X_points, Y_points))
    
    item_order = itertools.product(range(X_points), range(Y_points))
    for (X,Y) in item_order: # iterate each space point
        
        if energy_end != -1:
            dIdV = data3D[energy_start:energy_end+1,X,Y]
        else:
            dIdV = data3D[:,X,Y]

        # Least squares fit               
        p,res,_,_ = np.linalg.lstsq(A_matrix, dIdV, rcond=None)
        
        # Predict on training x (energy) to compute R^2
        dIdV_pred = A_matrix @ p
        
        # R^2 for this pixel
        ss_res = np.sum((dIdV - dIdV_pred) ** 2)
        ss_tot = np.sum((dIdV - np.mean(dIdV)) ** 2)
        if ss_tot < 1e-15:
            r2 = 1.0 if ss_res < 1e-15 else 0.0
        else:
            r2 = 1.0 - ss_res / ss_tot
        R2map[X, Y] = r2
        
        dIdV_Fitted = np.poly1d(p[::-1])
        dIdV_derivative = np.polyder(dIdV_Fitted, 1)
        dIdV_second_order_derivative = np.polyder(dIdV_Fitted, 2)
        roots = dIdV_derivative.r
        real_roots = roots[np.isreal(roots)].real 
        
        max_value_root = None 
        max_value = -np.inf
        for root in real_roots:
            if dIdV_second_order_derivative(root) < 0 and np.min(energy) <= root <= np.max(energy):
                value_at_root = dIdV_Fitted(root)
                if value_at_root > max_value:
                    max_value = value_at_root
                    max_value_root = root
        if max_value_root == None and dIdV_Fitted(np.max(energy)) > dIdV_Fitted(np.min(energy)):
            max_value_root = np.max(energy)
        elif max_value_root == None and dIdV_Fitted(np.max(energy)) < dIdV_Fitted(np.min(energy)):
            max_value_root = np.min(energy)
        
        gapmap[X,Y] = max_value_root
        
                
    gapmap = gapmap[np.newaxis,:,:]
    R2map = R2map[np.newaxis,:,:]
        
    return gapmap, R2map


 
    
    
    