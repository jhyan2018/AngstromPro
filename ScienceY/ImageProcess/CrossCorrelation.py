# -*- coding: utf-8 -*-
"""
Created on Mon Apr 22 15:37:42 2024

@author: Huiyu
"""
import numpy as np
from scipy.signal import correlate2d

def CrossCorrelation(data2Da, data2Db):
    
    data2Da_mean_subtracted = data2Da - np.mean(data2Da)
    data2Db_mean_subtracted = data2Db - np.mean(data2Db)
    
    cross_corr = correlate2d(data2Da_mean_subtracted, data2Db_mean_subtracted, mode = 'same', boundary='fill', )
    norm = np.sqrt((data2Da_mean_subtracted**2).sum() * (data2Db_mean_subtracted**2).sum())
    normalized_cross_corr = cross_corr / norm
    
    return normalized_cross_corr

