# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 11:19:50 2024

@author: Huiyu
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
from .GeometricOperation import AffineTransform

"""
function Module
"""

def register(data3D, r1Px1,r1Py1, r1Px2,r1Py2, r1Px3,r1Py3, r2Px1,r2Py1, r2Px2,r2Py2, r2Px3,r2Py3):
    '''
    Parameters
    ----------
    data3D : TYPE
        DESCRIPTION.
    rPx1 : TYPE
       

    Returns
    -------
    Affine Matrix A
    '''
    
    