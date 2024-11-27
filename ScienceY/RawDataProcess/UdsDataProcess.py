# -*- coding: utf-8 -*-
"""
Created on Mon Jul 24 14:47:18 2023

@author: Jiahao Yan
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

class UdsDataStru():

    def __init__(self,data,name):        
        self.data = np.copy(data)
        self.name = name
        self.axis_name = []
        self.axis_value = []
        self.info = dict()
        self.config = dict()
        self.proc_history = []
        self.proc_to_do = []
         
class UdsDataProcess():
    def __init__(self, path):
        self.path = path
        self.uds_data = 0
        self.data_starter = 0
        
    def saveToFile(self, uds_data):        
        self.uds_data = uds_data
        self.saveHead()
        self.saveData()
    
    def readFromFile(self):
        f = open(self.path, 'rb')
        
        # name
        name = f.readline().decode('utf-8').strip()
        
        # shape
        shape_text = f.readline().decode('utf-8').strip().split('=')[-1].split(',')
        shape = []
        for s in shape_text:
            shape.append(int(s))
        
        # data type
        data_type = f.readline().decode('utf-8').strip().split('=')[-1]
        
        # axis name
        axis_name = f.readline().decode('utf-8').strip().split('=')[-1]
        
        # axis value
        axis_value = f.readline().decode('utf-8').strip().split('=')[-1]
        
        info_starter = f.tell()
        
        # data
        while 1:
            line = f.readline().decode().strip()
            if line == ':HEADER_END:' :
                self.data_starter = f.tell()
                break
        
        raw_data1D = np.fromfile(f, dtype = data_type, count = -1)
        
        if len(shape) == 1: # 1D
            data = raw_data1D.reshape((shape[0]))
            self.uds_data = UdsDataStru(data, name)
        elif len(shape) == 2: # 2D
            data = raw_data1D.reshape((shape[0], shape[1]))
            self.uds_data = UdsDataStru(data, name)
        elif len(shape) == 3: # 3D
            data = raw_data1D.reshape((shape[0], shape[1], shape[2]))
            self.uds_data = UdsDataStru(data, name)
            print('3D data readed!')
        else:
            print('Unknown shape of readed uds data.')
            data = np.zeros((100,100))
            self.uds_data = UdsDataStru(data, 'uds3D_'+name)
        
        # info
        f.seek(info_starter, 0)
        while 1:
            line = f.readline().decode('utf-8').strip()
            if line == ':INFO_END:' :
                break
            key = line.split('=')[0]
            value = line.split('=')[1]
            self.uds_data.info[key] = value
            
        # axis name
        self.uds_data.axis_name = axis_name.split(',')
        
        # axis value
        axis_value_text_list = axis_value.split(';')
        axis_value_list = []
        for av_txt in axis_value_text_list:
            if not '&' in av_txt:
                av_float = list(map(float,av_txt.split(',')))

            else:
                av_cpl = av_txt.split(',')
                av_float = []
                for av_cpl_txt in av_cpl:
                    av_cpl_float = list(map(float,av_cpl_txt.split('&')))
                    av_float.append(av_cpl_float)
            axis_value_list.append(av_float)
        self.uds_data.axis_value = axis_value_list       
                   
        # proc_history
        while 1:
            line = f.readline().decode('utf-8').strip()
            if line == ':PROC_HISTORY_END:' :
                break
            self.uds_data.proc_history.append(line)
            
        # proc_to_do
        while 1:
            line = f.readline().decode('utf-8').strip()
            if line == ':HEADER_END:' :
                break
            self.uds_data.proc_to_do.append(line)
        
        #
        f.close()
        
        return self.uds_data
    
    def saveHead(self):
        f = open(self.path, 'wb')
        
        #
        name = self.uds_data.name+'\n'
        f.write(name.encode('utf-8'))
        
        # data shape
        shape_text = []
        for n in self.uds_data.data.shape:
            shape_text.append(str(n))
        separator = ','
        shape = 'Shape=' + separator.join(shape_text) + '\n'
        f.write(shape.encode('utf-8'))
        
        # data type
        data_type = 'DataType=' + self.uds_data.data.dtype.name + '\n'
        f.write(data_type.encode('utf-8'))
        
        # axis name
        axis_name = 'Axis Name=' + separator.join(self.uds_data.axis_name) + '\n'
        f.write(axis_name.encode('utf-8'))
        
        # axis value
        axis_value_text = []
        separator_l1 = ';'
        separator_l2 = ','
        separator_l3 = '&'
        for av in self.uds_data.axis_value:
            if type(av[0]) == list:
                av_cpl_txt = []
                for av_cpl in av:
                    av_cpl_str = list(map(str, av_cpl))
                    av_cpl_txt.append(separator_l3.join(av_cpl_str))
                axis_value_text.append(separator_l2.join(av_cpl_txt))
            else:
                av_str = list(map(str, av))
                axis_value_text.append(separator_l2.join(av_str))
        axis_value = 'Axis Value=' + separator_l1.join(axis_value_text) + '\n'
        f.write(axis_value.encode('utf-8'))
        
        #
        info = []
        if len(self.uds_data.info) > 0:
            for i in self.uds_data.info:
                v = self.uds_data.info[i]
                info.append((i + '=' + v + '\n').encode('utf-8'))
            f.writelines(info)            
        f.write(':INFO_END:\n'.encode('utf-8'))
        
        proc_history = []
        if len(self.uds_data.proc_history) > 0:
            for history in self.uds_data.proc_history:
                proc_history.append((history + '\n').encode('utf-8'))
            f.writelines(proc_history)
        f.write(':PROC_HISTORY_END:\n'.encode('utf-8'))
        
        proc_to_do = []
        if len(self.uds_data.proc_to_do) > 0:
            for to_do in self.uds_data.proc_to_do:
                proc_to_do.append((to_do + '\n').encode('utf-8'))
            f.writelines(proc_to_do)
        f.write(':HEADER_END:\n'.encode('utf-8'))        
        
        self.data_starter = f.tell()
        
        f.close()
    
    def saveData(self):
        f = open(self.path, 'ab')
        f.seek(self.data_starter, 0)
        
        self.uds_data.data.tofile(f)
        
        f.close()

        