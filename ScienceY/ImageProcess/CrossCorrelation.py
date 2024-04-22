# -*- coding: utf-8 -*-
"""
Created on Mon Apr 22 15:37:42 2024

@author: Huiyu
"""
import numpy as np
from scipy.signal import correlate

def CrossCorrelation(data3Da, data3Db):
    
    cross_corr = correlate(data3Da, data3Db, mode = 'same')
    norm = np.sqrt((data3Da**2).sum() * (data3Db**2).sum())
    normalized_cross_corr = cross_corr / norm
    
    return normalized_cross_corr

