# -*- coding: utf-8 -*-
"""
Created on Mon Sep 25 22:30:10 2023

@author: Jiahao Yan
"""

"""
System modules
"""

"""
Third-party Modules
"""

"""
User Modules
"""

"""
function Module
"""

class ProcessParameters():
    def __init__(self, procFunction):
        self.procFunction = procFunction
        self.p = []
        
        self.getDefaultParameters()
        
    def getDefaultParameters(self):
        if self.procFunction == 'actGenerateHeavisideCurve':
            self.p.append(512)    #size
            self.p.append(0)      #edge_x
            self.p.append(0)      #edge_y
        elif self.procFunction == 'actGenerateCircleCurve':
            self.p.append(512)    #size
            self.p.append(10)     #radius
            self.p.append(0)      #center_x
            self.p.append(0)      #center_y
        elif self.procFunction == 'actGenerateGaussianCurve':
            self.p.append(512)    #size
            self.p.append(10)     #Sigma
            self.p.append(0)      #center_x
            self.p.append(0)      #center_y
        elif self.procFunction == 'actGeneratePerfectLattice':
            self.p.append(20)     #m
            self.p.append(20)     #n
            self.p.append(10)     #a1x
            self.p.append(0)      #a1y
            self.p.append(0)      #a2x
            self.p.append(10)     #a2y
            self.p.append(None)           #atomSize
            self.p.append('Gaussian')     #atomCurve
            self.p.append(0)      #Ox
            self.p.append(0)      #Oy
            self.p.append(1)      #p1
            self.p.append(1)      #p2
        elif self.procFunction == 'actGenerateLatticeWithLineDomainWall':
            self.p.append(20)     #m
            self.p.append(20)     #n
            self.p.append(10)     #a1x
            self.p.append(0)      #a1y
            self.p.append(0)      #a2x
            self.p.append(10)     #a2y
            self.p.append(None)           #atomSize
            self.p.append(0.25)           #shiftDistance
            self.p.append('Gaussian')     #atomCurve
            self.p.append(0)      #Ox
            self.p.append(0)      #Oy
        elif self.procFunction == 'actGenerateLatticeWithPeriodicDistortions':            
            self.p.append(20)     #m
            self.p.append(20)     #n
            self.p.append(10)     #a1x
            self.p.append(0)      #a1y
            self.p.append(0)      #a2x
            self.p.append(10)     #a2y
            self.p.append(40)     #d1x
            self.p.append(0)      #d1y
            self.p.append(0)      #d2x
            self.p.append(0)      #d2y
            self.p.append(0.25)   #dpA1
            self.p.append(0)      #dpA2
            self.p.append(None)           #atomSize
            self.p.append('Gaussian')     #atomCurve
            self.p.append(0)      #Ox 
            self.p.append(0)      #Oy
            self.p.append(0.79)   #dPhi1
            self.p.append(0.79)   #dPhi2
    
    def setParameters(self, params):
        if self.procFunction == 'actGenerateHeavisideCurve':
            if len(params) > 0:
                param_numbers = len(params.split(','))
                if param_numbers > 0:
                    self.p[0] = int(params.split(',')[0])
                if param_numbers > 1:
                    self.p[1] = int( params.split(',')[1] )
                if param_numbers > 2:
                    self.p[2] = int( params.split(',')[2] )
                    
        elif self.procFunction == 'actGenerateCircleCurve':
            if len(params) > 0:
                param_numbers = len(params.split(','))
                if param_numbers > 0:
                    self.p[0] = int(params.split(',')[0])
                if param_numbers > 1:
                    self.p[1] = int( params.split(',')[1] )
                if param_numbers > 2:
                    self.p[2] = int( params.split(',')[2] )
                if param_numbers > 3:
                    self.p[3] = int( params.split(',')[3] )
        elif self.procFunction == 'actGenerateGaussianCurve':
            if len(params) > 0:
                param_numbers = len(params.split(','))
                if param_numbers > 0:
                    self.p[0] = int(params.split(',')[0])
                if param_numbers > 1:
                    self.p[1] = float( params.split(',')[1] )
                if param_numbers > 2:
                    self.p[2] = int( params.split(',')[2] )
                if param_numbers > 3:
                    self.p[3] = int( params.split(',')[3] )
        elif self.procFunction == 'actGeneratePerfectLattice':
            if len(params) > 0:
                param_numbers = len(params.split(','))
                if param_numbers > 0:
                    self.p[0] = int(params.split(',')[0])
                if param_numbers > 1:
                    self.p[1] = int( params.split(',')[1] )
                if param_numbers > 2:
                    self.p[2] = float( params.split(',')[2] )
                if param_numbers > 3:
                    self.p[3] = float( params.split(',')[3] )
                if param_numbers > 4:
                    self.p[4] = float( params.split(',')[4] )
                if param_numbers > 5:
                    self.p[5] = float( params.split(',')[5] )
                if param_numbers > 6:
                    self.p[6] = float( params.split(',')[6] )
                if param_numbers > 7:
                    self.p[7] = params.split(',')[7]
                if param_numbers > 8:
                    self.p[8] = float( params.split(',')[8] )
                if param_numbers > 9:
                    self.p[9] = float( params.split(',')[9] )
                if param_numbers > 10:
                    self.p[10] = float( params.split(',')[10] )
                if param_numbers > 11:
                    self.p[11] = float( params.split(',')[11] )
        elif self.procFunction == 'actGenerateLatticeWithLineDomainWall':
            if len(params) > 0:
                param_numbers = len(params.split(','))
                if param_numbers > 0:
                    self.p[0] = int(params.split(',')[0])
                if param_numbers > 1:
                    self.p[1] = int( params.split(',')[1] )
                if param_numbers > 2:
                    self.p[2] = float( params.split(',')[2] )
                if param_numbers > 3:
                    self.p[3] = float( params.split(',')[3] )
                if param_numbers > 4:
                    self.p[4] = float( params.split(',')[4] )
                if param_numbers > 5:
                    self.p[5] = float( params.split(',')[5] )
                if param_numbers > 6:
                    self.p[6] = float( params.split(',')[6] )
                if param_numbers > 7:
                    self.p[7] = float( params.split(',')[7] )
                if param_numbers > 8:
                    self.p[8] = params.split(',')[8]
                if param_numbers > 9:
                    self.p[9] = float( params.split(',')[9] )
                if param_numbers > 10:
                    self.p[10] = float( params.split(',')[10] )
        elif self.procFunction == 'actGenerateLatticeWithPeriodicDistortions':
            if len(params) > 0:
                param_numbers = len(params.split(','))
                if param_numbers > 0:
                    self.p[0] = int(params.split(',')[0])
                if param_numbers > 1:
                    self.p[1] = int( params.split(',')[1] )
                if param_numbers > 2:
                    self.p[2] = float( params.split(',')[2] )
                if param_numbers > 3:
                    self.p[3] = float( params.split(',')[3] )
                if param_numbers > 4:
                    self.p[4] = float( params.split(',')[4] )
                if param_numbers > 5:
                    self.p[5] = float( params.split(',')[5] )
                if param_numbers > 6:
                    self.p[6] = float( params.split(',')[6] )
                if param_numbers > 7:
                    self.p[7] = float( params.split(',')[7] )
                if param_numbers > 8:
                    self.p[8] = float( params.split(',')[8] )
                if param_numbers > 9:
                    self.p[9] = float( params.split(',')[9] )                
                if param_numbers > 10:
                    self.p[10] = float( params.split(',')[10] )
                if param_numbers > 11:
                    self.p[11] = float( params.split(',')[11] )                
                if param_numbers > 12:
                    self.p[12] = float( params.split(',')[12] )
                if param_numbers > 13:
                    self.p[13] = params.split(',')[13]
                if param_numbers > 14:
                    self.p[14] = float( params.split(',')[14] )
                if param_numbers > 15:
                    self.p[15] = float( params.split(',')[15] )
                if param_numbers > 16:
                    self.p[16] = float( params.split(',')[16] )
                if param_numbers > 17:
                    self.p[17] = float( params.split(',')[17] )