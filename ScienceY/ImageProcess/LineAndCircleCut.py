#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct  9 11:54:22 2024

@author: zhaohuiyu

  if order == 0:
    interpolate_method = 'nearest'  
  elif order == 1:
    interpolate_method = 'bilinear'
  elif order == 2:
    interpolate_method = 'biquadratic'
  elif order == 3:
        interpolate_method = 'bicubic'
    
  default order = 1

"""
import numpy as np
from scipy.ndimage import map_coordinates


class LineCut():
    
    def __init__(self, data3D, lCPx1, lCPy1, lCPx2, lCPy2, order = 1, num_points = None):
        self.data3D = data3D
        self.x1 = lCPx1
        self.y1 = lCPy1
        self.x2 = lCPx2
        self.y2 = lCPy2
        self.order = order
        self.num_points = num_points if num_points else int(np.hypot(lCPx2-lCPx1, lCPy2-lCPy1))
        
    def bresenham_line(self):
        points = []
        x1 = self.x1
        y1 = self.y1
        x2 = self.x2
        y2 = self.y2
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        while True:
            points.append((x1, y1))
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy
                
        points = np.array(points)
        linecut_values = [self.data3D[:,y,x] for x,y in points]
    
        return np.array(linecut_values), points
    
    
    
    def linecut_interpolated(self):
        
        x_coords = np.linspace(self.x1, self.x2, self.num_points)
        y_coords = np.linspace(self.y1, self.y2, self.num_points)
        
        linecut_values = np.zeros((self.data3D.shape[0], self.num_points))
        # Map the input array to new coordinates by interpolation
        for i in range(self.data3D.shape[0]):
            linecut_values[i,:] = map_coordinates(self.data3D[i], [y_coords, x_coords], order = self.order)
        
        linecut_points = np.column_stack((x_coords, y_coords)) # the shape of linecut_points is (num_points,2)
        
        return linecut_values, linecut_points
    
    
    # Get the points perpendicular to the direction of the linecut and get their values by interpolation
    def get_perpendicular_points(self, data, x, y, W): # data is two dimentional
        half_W = W / 2
        direction_dx = self.x2 - self.x1
        direction_dy = self.y2 - self.y1
        num_nearby_points = int(W)
        length = np.sqrt(direction_dx**2 + direction_dy**2)
        if length == 0:
            return np.array([data[self.y1, self.x1]]), [self.x1], [self.y1]
        
        
        perp_dx = -direction_dy / length
        perp_dy = direction_dx / length
        
        offsets = np.linspace(-half_W, half_W, num_nearby_points)
        nearby_x = x + offsets * perp_dx
        nearby_y = y + offsets * perp_dy
        
        # 
        nearby_values = map_coordinates(data, [nearby_y, nearby_x], order = self.order)
        
        return nearby_values, nearby_x, nearby_y
        
    # Calculate the average value vs. distance across the vertical width of the linecut
    def linecut_with_width_average(self, W):

        linecut_values, linecut_points = self.linecut_interpolated()
        linecut_x, linecut_y = linecut_points[:,0], linecut_points[:,1]
        
        average_values = np.zeros((self.data3D.shape[0], self.num_points))
        all_nearby_points_x = []
        all_nearby_points_y = []
        
        
        for j in range(self.data3D.shape[0]):
            for i in range(self.num_points):
                nearby_values, nearby_x, nearby_y = self.get_perpendicular_points(self.data3D[j,:,:], linecut_x[i], linecut_y[i], W)

                avg_value = np.mean(nearby_values)
                average_values[j,i] = avg_value
            
                all_nearby_points_x.extend(nearby_x)
                all_nearby_points_y.extend(nearby_y)
        
        nearby_points = np.column_stack((all_nearby_points_x, all_nearby_points_y))
        
        return average_values, linecut_points, nearby_points
    
    

class CircleCut:
    
    def __init__(self, data3D, CCPx1, CCPy1, CCPx2, CCPy2, order = 1, num_points = None):
        self.data3D = data3D
        self.x1 = CCPx1
        self.y1 = CCPy1
        self.x2 = CCPx2
        self.y2 = CCPy2
        self.order = order
        self.num_points = num_points if num_points else int(2 * np.pi * np.hypot(CCPx2-CCPx1, CCPy2 - CCPy1))
    
    def circlecut_interpolated(self):
        
        radius = np.sqrt((self.x2 - self.x1) ** 2 + (self.y2 - self.y1) ** 2)
        theta = np.linspace(0, 2 * np.pi, self.num_points)
        
        x_coords = self.x1 + radius * np.cos(theta)
        y_coords = self.y1 + radius * np.sin(theta)
        
        circlecut_values = np.zeros((self.data3D.shape[0], self.num_points))
        for i in range(self.data3D.shape[0]):
            circlecut_values[i, :] = map_coordinates(self.data3D[i], [y_coords, x_coords], order = self.order)
        
        circlecut_points = np.column_stack((x_coords, y_coords))
        
        return circlecut_values, circlecut_points
    

    def get_perpendicular_points_circle(self, data, x, y, W):
    
        half_W = W / 2.0
        direction_dx = x - self.x1
        direction_dy = y - self.y1
        num_nearby_points = int(W)
        length = np.hypot(direction_dx, direction_dy)
        
        if length == 0:
            return np.array([data[self.y1, self.x1]]), [self.x1], [self.y1]
        
        perp_dx = direction_dx / length
        perp_dy = direction_dy / length
        
        # Generates coordinates in the vertical direction
        offsets = np.linspace(-half_W, half_W, num_nearby_points)
        nearby_x = x + offsets * perp_dx
        nearby_y = y + offsets * perp_dy
        
        nearby_values = map_coordinates(data, [nearby_y, nearby_x], order = self.order)
        
        return nearby_values, nearby_x, nearby_y
    
    def circlecut_with_width_average_circle(self, W):
        
        circlecut_values, circlecut_points = self.circlecut_interpolated()
        circlecut_x, circlecut_y = circlecut_points[:,0], circlecut_points[:,1]
        
        average_values = np.zeros((self.data3D.shape[0], self.num_points))
        all_nearby_points_x = []
        all_nearby_points_y = []
        
        for j in range(self.data3D.shape[0]):
            for i in range(self.num_points):
                
                nearby_values, nearby_x, nearby_y = self.get_perpendicular_points_circle(self.data3D[j,:,:], circlecut_x[i], circlecut_y[i], W)
    
                avg_value = np.mean(nearby_values)
                average_values[j, i] = avg_value
                
                all_nearby_points_x.extend(nearby_x)
                all_nearby_points_y.extend(nearby_y)
        
        nearby_points = np.column_stack((all_nearby_points_x, all_nearby_points_y))
        
        return average_values, circlecut_points, nearby_points
    
    
    
    
    
    