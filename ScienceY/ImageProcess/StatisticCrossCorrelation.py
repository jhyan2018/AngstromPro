# -*- coding: utf-8 -*-
"""
Created on Fri Apr 19 16:51:14 2024

@author: Huiyu
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
def StatisticCrossCorrelation(data2Da, data2Db, size = 100, sigma = 3):
    '''
    Parameters
    ----------
    data2Da : image in main
        The horizontal axis
    data2Db : image in slave
        The vertical axis, need to be registered with image in main
    size : the pixels in processed image
        DESCRIPTION. The default is 100.
    sigma :  the Certain number of standard deviations
        Selecting data that falls within a certain number of standard deviations 
        from the mean in the datasets main and slave. The default is 3.

    Returns
    -------
    statis_result : statistic cross correlation
        The origin is the point at the bottom left of the image
        the horizontal axis represents the intensity of the data in main
        and the vertical axis represents the intensity of the data in slave

    '''
    data_r = data2Da.shape[0]
    data_c = data2Da.shape[1]
    n = sigma
    inter_num = size
    
    statis_result = np.zeros((inter_num, inter_num))
    
    mu_a = np.mean(data2Da)
    sigma_a = np.std(data2Da)
    a_inter = 2 * n * sigma_a / inter_num
    a_min = mu_a - n * sigma_a
    
    mu_b = np.mean(data2Db)
    sigma_b = np.std(data2Db)
    b_inter = 2 * n * sigma_b / inter_num
    b_min = mu_b - n * sigma_b
    
    for i in range(data_r):
        for j in range(data_c): # Traverse space points
            a_index = int((data2Da[i, j] - a_min) / a_inter)
            b_index = int((data2Db[i, j] - b_min) / b_inter)
            if 0 <= a_index < inter_num and 0 <= b_index < inter_num:
                statis_result[inter_num - b_index - 1, a_index] += 1
    
    
    return statis_result
    