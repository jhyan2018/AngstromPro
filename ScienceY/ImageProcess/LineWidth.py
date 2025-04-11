#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr  4 16:09:23 2025

@author: zhaohuiyu
"""
import numpy as np

def LineWidth(data3D, LayerValue, p, energy_start = 0, energy_end = -1):
    
    if energy_end != -1:
        x = np.array(LayerValue)[energy_start:energy_end+1]
    else:
        x = np.array(LayerValue)



    # Initialize the output 2D array for storing FWHM values
    height, width = data3D.shape[1], data3D.shape[2]
    fwhm_map = np.zeros((height, width))
    a_inverse_map = np.zeros((height, width))

    # Iterate over each pixel (i, j) position
    # For each pixel, fit a 2nd-degree polynomial using the 5 data points from dimension 0
    for i in range(height):
        for j in range(width):
            y = data3D[:, i, j]
        
            # Perform quadratic (2nd-degree) polynomial fitting
            coeffs = np.polyfit(x, y, deg=2)
            a, b, c = coeffs
            a_inverse_map[i,j] = 1/a
            
            # Check if the leading coefficient is zero (i.e., not a quadratic)
            if a == 0:
                fwhm_map[i, j] = 0
                continue

            # Calculate the x-coordinate of the vertex (peak)
            x_peak = -b / (2 * a)
            # Calculate the y-value at the peak
            y_peak = np.polyval(coeffs, x_peak)
            # Define the half maximum level
            y_half = y_peak / 2

            # Solve the quadratic equation: a2*x^2 + b2*x + (c2 - y_half) = 0
            delta = b**2 - 4 * a * (c - y_half)
            if delta < 0:
                # No real solution, assign 0
                fwhm_map[i, j] = 0
            else:
                sqrt_delta = np.sqrt(delta)
                x1 = (-b - sqrt_delta) / (2 * a)
                x2 = (-b + sqrt_delta) / (2 * a)
                # Full Width at Half Maximum (FWHM) is the distance between the two roots
                fwhm_map[i, j] = abs(x2 - x1)
    
    fwhm_map = fwhm_map[np.newaxis,:,:]
    a_inverse_map = a_inverse_map[np.newaxis,:,:]
                
    if p == 'linewidth':
        return fwhm_map
    
    if p == 'a inverse':
        return a_inverse_map

