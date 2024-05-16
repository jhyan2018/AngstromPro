# -*- coding: utf-8 -*-
"""
Created on Wed Sep 13 14:03:55 2023

@author: Jiahao Yan & Huiyu Zhao
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
from ..ImageSimulate.GenerateCurve2D import gaussian2D
"""
function Module
"""

class LockIn2D():
    def __init__(self, data2D, px, py, rSigma): # data2D should be a square matrix
               
        # calculate equivalent k-space Gaussian function with respect to r-space Gaussian
        N = data2D.shape[-1]
        kSigma = N / (2 * np.pi * rSigma)
        kFactor = 2 * np.pi * (rSigma**2)
        #print("2D Lockin KSigma:", kSigma)
        
        kGaussian = kFactor * gaussian2D(N, kSigma)
        
        # calculate A_Q(k)
        O_kx = (N - N%2)/2
        O_ky = (N - N%2)/2
        
        Qx = 2 * np.pi * (px - O_kx) / N
        Qy = 2 * np.pi * (py - O_ky) / N
        
        x = np.arange(N)
        y = np.arange(N)
        X,Y = np.meshgrid(x,y)
        '''
        nr, nc = data2D.shape
        
        xp = np.linspace(0, np.pi, nc)
        yp = np.linspace(0, np.pi, nr)
        z = np.outer(np.sin(xp), np.sin(yp))
        '''
        eQR = np.exp( 1j * ( Qx * X + Qy * Y) )
        
        A_Q_k = np.fft.fftshift( np.fft.fft2( data2D * eQR ) )
        
        # calculate A_Q(r)
        self.A_Q_r =np.fft.ifft2( np.fft.ifftshift( A_Q_k * kGaussian ) ) 
    
    # Old PhaseUnwrap Methods
    def phaseUnwrap(self, phaseReverseFactor=0.8):
        #phaseMapWrapped = np.arctan2( np.imag(self.A_Q_r), np.real(self.A_Q_r) )
        phaseMapWrapped = np.angle(self.A_Q_r)
        phaseMapRegions = np.zeros_like(phaseMapWrapped)
        
        for col in range(self.A_Q_r.shape[-1]):
            n = 0
            for row in range(self.A_Q_r.shape[-2] - 1):
                if phaseMapWrapped[row+1,col] * phaseMapWrapped[row,col] <  - phaseReverseFactor * np.pi**2 :
                    if phaseMapWrapped[row+1,col] > 0:
                        n -= 1
                    else:
                        n += 1
                phaseMapRegions[row+1,col] = n
        
        phaseMapRegions[0,:] = phaseMapRegions[1,:]
        
        phaseMapUnwrapped = phaseMapWrapped + 2*np.pi*phaseMapRegions + np.pi
        
        return phaseMapUnwrapped
    
    def get_reliability(self, img):
        rel = np.zeros_like(img)

        # get the shifted images (N-2, N-2)
        img_im1_jm1 = img[:-2, :-2]
        img_i_jm1 = img[1:-1, :-2]
        img_ip1_jm1 = img[2:, :-2]
        img_im1_j = img[:-2, 1:-1]
        img_i_j = img[1:-1, 1:-1]
        img_ip1_j = img[2:, 1:-1]
        img_im1_jp1 = img[:-2, 2:]
        img_i_jp1 = img[1:-1, 2:]
        img_ip1_jp1 = img[2:, 2:]

        # calculate the difference
        def gamma(x):
            return np.sign(x) * np.mod(np.abs(x), np.pi)

        H = gamma(img_im1_j - img_i_j) - gamma(img_i_j - img_ip1_j)
        V = gamma(img_i_jm1 - img_i_j) - gamma(img_i_j - img_i_jp1)
        D1 = gamma(img_im1_jm1 - img_i_j) - gamma(img_i_j - img_ip1_jp1)
        D2 = gamma(img_im1_jp1 - img_i_j) - gamma(img_i_j - img_ip1_jm1)

        # calculate the second derivative
        D = np.sqrt(H ** 2 + V ** 2 + D1 ** 2 + D2 ** 2)

        # assign the reliability as 1 / D
        rel[1:-1, 1:-1] = 1.0 / D

        # assign all nan's in rel with non-nan in img to 0
        rel[np.isnan(rel) & ~np.isnan(img)] = 0
        rel[np.isnan(img)] = np.nan

        return rel
    
    def get_edges(self, rel):
        Ny, Nx = rel.shape
        h_edges = np.column_stack( (rel[:, 1:] + rel[:, :-1], np.nan * np.ones((Ny, 1)) ) )
        v_edges = np.row_stack((rel[1:, :] + rel[:-1, :], np.nan * np.ones((1, Nx))))
        return h_edges, v_edges
    
    
    def unwrap_phase(self,img):
        Ny, Nx = img.shape
    
        # get the reliability
        reliability = self.get_reliability(img)
    
        # get the edges
        h_edges, v_edges = self.get_edges(reliability)
    
        # combine all edges and sort them
        edges = np.concatenate((h_edges.ravel(), v_edges.ravel()))
        edge_bound_idx = Ny * Nx
        edge_sort_idx = np.argsort(edges)[::-1]
    
        # get the indices of pixels adjacent to the edges
        idxs1 = edge_sort_idx % edge_bound_idx
        idxs2 = np.where(edge_sort_idx < edge_bound_idx,
                         idxs1 + 1, idxs1 + Nx)
    
        # Fix out-of-bound indices for horizontal edges at the right border
        horizontal_mask = edge_sort_idx < edge_bound_idx
        right_border_mask = (idxs1 % Nx) == (Nx - 1)
        idxs2[horizontal_mask & right_border_mask] -= 1
    
        # Fix out-of-bound indices for vertical edges at the bottom border
        vertical_mask = edge_sort_idx >= edge_bound_idx
        bottom_border_mask = (idxs1 // Nx) == (Ny - 1)
        idxs2[vertical_mask & bottom_border_mask] -= Nx
    
        # label the group
        group = np.arange(Ny * Nx).reshape(Ny, Nx)
        is_grouped = np.zeros(Ny * Nx, dtype=bool)
        group_members = {i: [i] for i in range(Ny * Nx)}
        num_members_group = np.ones(Ny * Nx, dtype=int)
    
        # propagate the unwrapping
        res_img = img.copy()
        num_nan = np.sum(np.isnan(edges))  # count how many nan-s and skip them
    
        for i in range(num_nan, len(edge_sort_idx)):
            # get the indices of the adjacent pixels
            idx1 = idxs1[i]
            idx2 = idxs2[i]
    
            # skip if they belong to the same group
            if group.ravel()[idx1] == group.ravel()[idx2]:
                continue
    
            # determine the grouping
            all_grouped = False
            if is_grouped[idx1]:
                if not is_grouped[idx2]:
                    idx1, idx2 = idx2, idx1
                elif num_members_group[group.ravel()[idx1]] > num_members_group[group.ravel()[idx2]]:
                    idx1, idx2 = idx2, idx1
                    all_grouped = True
                else:
                    all_grouped = True
    
            # calculate how much we should add to the idx1 and group
            dval = np.floor((res_img.ravel()[idx2] - res_img.ravel()[idx1] + np.pi) / (2 * np.pi)) * 2 * np.pi
    
            # which pixel should be changed
            g1 = group.ravel()[idx1]
            g2 = group.ravel()[idx2]
            if all_grouped:
                pix_idxs = group_members[g1]
            else:
                pix_idxs = [idx1]
    
            # add the pixel value
            if dval != 0:
                res_img.ravel()[pix_idxs] += dval
    
            # change the group
            len_g1 = num_members_group[g1]
            len_g2 = num_members_group[g2]
            group_members[g2].extend(pix_idxs)
            group.ravel()[pix_idxs] = g2  # assign the pixels to the new group
            num_members_group[g2] += len_g1
    
            # mark idx1 and idx2 as already being grouped
            is_grouped[idx1] = True
            is_grouped[idx2] = True
    
        return res_img
    
    def getPhaseMap(self, phaseUnwrap=True, phaseReverseFactor=0.8):
        #phaseMap = np.arctan2( np.imag(self.A_Q_r), np.real(self.A_Q_r) ) + np.pi
        phaseMap = np.angle(self.A_Q_r) + np.pi
        
        if phaseUnwrap == True:
            #phaseMap = self.phaseUnwrap(phaseReverseFactor)
            phaseMap = self.unwrap_phase(phaseMap)
            
        return phaseMap
               
    def getAmplitudeMap(self):
        return np.abs( self.A_Q_r )
    
