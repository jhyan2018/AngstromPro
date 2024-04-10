# -*- coding: utf-8 -*-
"""
Created on Mon Aug  7 17:29:10 2023

@author: Jiahao Yan
"""

"""
System modules
"""
import sys, os
import itertools
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
def backgroundSubtract2DPlane(data2D, order=1):
    '''
    Parameters
    ----------
    data2D : Two-dimensional data needed to be processed.
    
    order : int
        1: Subtracting the linear background.
        2: Subtracting the second-order background.
        ......
        The default is 1.

    Return the two-dimensional data without background.
    -------
    Subtract a background, which is an n-th order two-dimensional surface.
    
    ### least square fitting ###
    
    fitting curve/surface:
        z = b 
            + k1 x + k2 y 
            + k3 x^2 + k4 y^2 + k5 xy
            + k6 x^3 + k7 y^3 + k8 x^2y + k9xy^2
            
    To get the best fittings for unkonwn parameters k1, k2, k3 ... can be sovled in matrix form,
    and all the points of (x_i, y_i, z_i) are known. 
    
    In the matrix form:
    A p = q, A is a matrix, p and q are vectors
    
    A = (1_>, x_>, y_>, x^2_>, y^2_>, xy_>, ... ),  x_> is a vector inlcuding all the known points on x axis
    p = (b, k1, k2, k3, k4, k5, ...)^T, T means transpose
    q = z_> , z_> is a vector including all the z value of all corresponding known points for fitting
    
    then, fitting of p = (A^T A)^-1 A^T q
    '''
    
    rows_data = data2D.shape[-2]
    columns_data = data2D.shape[-1]
    
    X,Y = np.meshgrid(np.arange(columns_data), np.arange(rows_data))
    
    # make all date points be in one dimension
    x_col_vect = X.reshape(columns_data*rows_data)
    y_col_vect = Y.reshape(columns_data*rows_data)
    z_col_vect = data2D.reshape(columns_data*rows_data)
    
    # 2D poly fit for getting b, k1, k2, k3, k4, k5, ...
    item_order = itertools.product(range(order+1), range(order+1))
    A_matrix_columns = 0
    for k, (i,j) in enumerate(item_order):
        if (i+j) <= order:
            A_matrix_columns += 1
            
            
    A_matrix = np.zeros((columns_data*rows_data, A_matrix_columns))
    item_order = itertools.product(range(order+1), range(order+1))
    col_idx = 0
    for k, (i,j) in enumerate(item_order):
        if (i+j) <= order:
            A_matrix[:,col_idx] = (x_col_vect**i) * (y_col_vect**j)
            col_idx += 1
            
    p,res,_,_ = np.linalg.lstsq(A_matrix, z_col_vect, rcond=None)
    
    # calculate the curve/surface to be subtracted
    Z_bg = np.zeros((rows_data,columns_data))
    item_order = itertools.product(range(order+1), range(order+1))
    col_idx = 0
    for k, (i,j) in enumerate(item_order):
        if (i+j) <= order:
            Z_bg += p[col_idx] * (X**i) * (Y**j)
            col_idx += 1
            
    # Subtract background
    Z_bg_subtracted = np.zeros((rows_data,columns_data))
    Z_bg_subtracted = data2D - Z_bg
    
    return Z_bg_subtracted
    
    
def backgroundSubtractPerLine(data2D, order=1):
    '''
    Parameters
    ----------
    data2D : Two-dimensional data needed to be processed.
    
    order : int
        1: Subtracting the linear background.
        2: Subtracting the second-order background.
        ......
        The default is 1.

    Returns the two-dimensional data without background
    -------
    subtract the background line by line.

    '''
    rows_data = data2D.shape[-2]
    columns_data = data2D.shape[-1]
    
    Z_bg_subtracted = np.zeros((rows_data, columns_data))
    Z_average = np.zeros(rows_data)
    Z_processed = np.zeros((rows_data, columns_data))
    
    # background subtract for each line
    for row_idx in range(rows_data):
        
        X = np.ones(columns_data)*row_idx # Equivalent to constant term
        Y = np.arange(columns_data)
        Z1D = data2D[row_idx,:]
        
        # Determine the number of columns of matrix A
        item_order = itertools.product(range(order+1), range(order+1))
        A_matrix_columns = 0
        for k, (i,j) in enumerate(item_order):
            if (i+j) <= order:
                A_matrix_columns += 1
        A_matrix = np.zeros((columns_data, A_matrix_columns))
        
        # Determine the matrix A
        item_order = itertools.product(range(order+1), range(order+1))
        col_idx = 0
        for k, (i,j) in enumerate(item_order):
            if (i+j) <= order:
                A_matrix[:,col_idx] = (X**i) * (Y**j)
                col_idx += 1
                        
        p,res,_,_ = np.linalg.lstsq(A_matrix, Z1D, rcond=None)
        
        # determine the background
        Z1D_bg = np.zeros(columns_data)
        item_order = itertools.product(range(order+1), range(order+1))
        col_idx = 0
        for k, (i,j) in enumerate(item_order):
            if (i+j) <= order:
                Z1D_bg += p[col_idx] * (X**i) * (Y**j)
                col_idx += 1
            
        # Subtract background & average
        Z_bg_subtracted[row_idx,:] = Z1D - Z1D_bg
        Z_average[row_idx] = np.average(Z_bg_subtracted[row_idx,:]) # Z_average is almost zero
        Z_processed[row_idx,:] = Z_bg_subtracted[row_idx,:]-Z_average[row_idx]  
    
    return Z_processed
    
     
    
    
    