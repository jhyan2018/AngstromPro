# -*- coding: utf-8 -*-
"""
Created on Thu Sep 21 22:51:09 2023

@author: Jiahao Yab
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
from .GenerateCurve2D import gaussian2D
"""
function Module
"""

"""
    lattice sites location    
    l(m,n) = m*a1 + n*a2 + u(m,n)   
    u(m,n) is the displacement
    
"""

class GenerateLattice2D():
    def __init__(self, m, n, a1x, a1y, a2x, a2y, Ox=0, Oy=0):                
        self.M, self.N = np.meshgrid( np.arange(m), np.arange(n))
                
        self.latticeSitesX = self.M*a1x + self.N*a2x + Ox
        self.latticeSitesY = self.M*a1y + self.N*a2y + Oy
        
        self.a1x = a1x
        self.a1y = a1y
        self.a2x = a2x
        self.a2y = a2y
        
        self.a1 = np.sqrt(a1x**2 + a1y**2)
        self.a2 = np.sqrt(a2x**2 + a2y**2)
        
        self.displacmentX = np.zeros_like(self.latticeSitesX)
        self.displacmentY = np.zeros_like(self.latticeSitesY)
                
    def setDisplacementLineDomainWall(self, shiftDistance): 
        for col in range(self.displacmentX.shape[-1]):
            for row in range(self.displacmentX.shape[-2]):
                if col >  self.displacmentX.shape[-1]/2:
                    self.displacmentX[row,col] = shiftDistance * min(self.a1, self.a2)
        
        self.latticeSitesX = self.latticeSitesX + self.displacmentX
        self.latticeSitesY = self.latticeSitesY + self.displacmentY
        
    def setDisplacementPeriodic(self, d1x, d1y, d2x, d2y, dpA1=0.1, dpA2=0.1, dPhi1=0, dPhi2=0): # maybe not right  

        if not d1x == 0:
            self.displacmentX = self.displacmentX + (dpA1*self.a1) * np.cos(2*np.pi*self.M*(self.a1x/d1x) + dPhi1)
        if not d2x == 0:
            self.displacmentX = self.displacmentX + (dpA2*self.a2) * np.cos(2*np.pi*self.N*(self.a2x/d2x) + dPhi2)
        if not d1y == 0:    
            self.displacmentY = self.displacmentY + (dpA1*self.a1) * np.cos(2*np.pi*self.M*(self.a1y/d1y) + dPhi1) 
        if not d2y == 0:
            self.displacmentY = self.displacmentY + (dpA2*self.a2) * np.cos(2*np.pi*self.N*(self.a2y/d2y) + dPhi2)
        
        self.latticeSitesX = self.latticeSitesX + self.displacmentX
        self.latticeSitesY = self.latticeSitesY + self.displacmentY
    
    def generateLattice2D(self, atomSize=None, atomCurve="Gaussian", p1=1, p2=1):

        if atomSize == None:
            atomSize = min(self.a1, self.a2) / 2
        
        rSpaceRangeX = np.ceil( np.amax(self.latticeSitesX) - np.amin(self.latticeSitesX) )
        rSpaceRangeY = np.ceil( np.amax(self.latticeSitesY) - np.amin(self.latticeSitesY) )
        rSpaceRange = int( max(rSpaceRangeX, rSpaceRangeY) )
        
        latticeCurve2D = np.zeros((rSpaceRange, rSpaceRange))
        
        for col in range(self.latticeSitesX.shape[-1]):
            for row in range(self.latticeSitesX.shape[-2]):
                if atomCurve == "Gaussian":
                    rSigma = 0.2 * atomSize
                    dCenterX = (rSpaceRange - rSpaceRange%2)/2
                    dCenterY = (rSpaceRange - rSpaceRange%2)/2
                    
                    latticeCurve2D += np.cos(2*np.pi* (col/p1 + row/p2)) * gaussian2D(rSpaceRange, rSigma, 
                                                 self.latticeSitesX[row,col] - dCenterX, 
                                                 self.latticeSitesY[row,col] - dCenterY)
                else:
                    pass
        
        return latticeCurve2D