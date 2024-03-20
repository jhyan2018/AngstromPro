'''
Load the Nanonis 3ds file data into dict named header and a 3D array named data3D.
Get the dI/dV map and Topo form the data3D
@author: Huiyu Zhao
Created on: Jul 20, 2023 

'''

"""
Third-party Modules
"""
import numpy as np
import re
"""
User Modules
"""
from ..RawDataProcess.UdsDataStru import UdsDataStru3D

"""
Class Definition
"""

'''
Load the header and data
'''

## Load 3ds file
class Load3ds():
    
    def __init__(self, path):
        self.path = path
        self.header = self.get_header()
        self.data3D = self.load_data()
        
    def get_header(self):
        f = open(self.path, 'rb')
        header = {}
        while 1:
            line = f.readline().decode().strip().replace('"', '')
            if line == ':HEADER_END:' :
                data_starter = f.tell()
                break
            line1 = line.split('=')
            s_key = line1[0].lower()
            s_val = line1[1]
            header.update({s_key : s_val})
        f.close()
        
        header['grid dim'] = list(map(int, header['grid dim'].split('x')))
        header['# parameters (4 byte)'] = int(header['# parameters (4 byte)'])
        header['points'] = int(header['points'])
        header['channels'] = header['channels'].split(';')
        header['fixed parameters'] = header['fixed parameters'].split(';')
        header['experiment parameters'] = header['experiment parameters'].split(';')
        header['grid settings'] = dict(zip(('Cx','Cy','W','H','A(deg)'), 
                                           tuple(map(float, header['grid settings'].split(';')))))
        header.update({'data starter' : data_starter})
        
        return header
        
    def load_data(self):
        par_num = self.header['# parameters (4 byte)']
        channels_num = len(self.header['channels'])
        points_num = self.header['points']
        
        # The data length occupied by each space point
        l = par_num+ channels_num*points_num
        
        f = open(self.path, 'rb')
        f.seek(self.header['data starter'], 0)
        raw_data1D = np.fromfile(f, dtype = '>f4', count = -1)        
        f.close()
        
        data2D = raw_data1D.reshape((-1, l))
        data3D = np.zeros((l, self.header['grid dim'][0], self.header['grid dim'][1]))
        
        for i in range(l):
            data3D[i,:,:] = data2D[:,i].reshape(self.header['grid dim'][0], self.header['grid dim'][1])
                    
        data3D = np.flip(data3D, axis=1)
        
        return data3D



## Load sxm file
class LoadSxm():
    
    def __init__(self, path):
        self.path = path
        self.header = self.get_header()
        self.data3D = self.load_data()
    
    def get_header(self):
        f = open(self.path, 'rb')
        header = {}
        caption = re.compile(':*:')
        while 1:
            line = f.readline().decode().strip()

            if line == ":SCANIT_END:": # check for end of header
                f.readline(); f.readline() # two blank lines
                data_starter = f.tell()
                header['data_starter'] = data_starter
                break
            if caption.match(line) != None:
                s_key = line[1:-1]  #set new name
                s_val = ''  #reset value
            else: #if not caption, it is content
                s_val = s_val + line + '\n'
            header.update({s_key : s_val.strip()})
        f.close()
        
        data_info = header['DATA_INFO']
        header['DATA_INFO'] = [] # change the type to list
        lines = data_info.split('\n')
        lines.pop(0) # remove the fist line: Channel    Name	Unit	Direction	Calibration	  Offset
        channels = []
        channels_num = 0
        for line in lines:
            val = line.split()
            if len(val) > 1:
                header['DATA_INFO'].append(val)
                channels.append(val[1])
                if val[3] != 'both':
                    print ('warning, only one direction recorded, expect a crash :D', val)
                    channels_num += 1
                else:
                    channels_num += 2
        header.update({'channels': channels})
        header.update({'channels_num': channels_num})
        
        xPixels, yPixels = header['SCAN_PIXELS'].split()
        xPixels = int(xPixels)
        yPixels = int(yPixels)
        header.update({'xPixels': xPixels})
        header.update({'yPixels': yPixels})
        
        ZController = header['Z-CONTROLLER']
        header['Z-CONTROLLER'] = {} #change the type to dictionary
        lines = ZController.split('\n')
        keys = lines[0].split('\t')
        vals = lines[1].split('\t')
        for i in range(len(keys)):
            header['Z-CONTROLLER'].update({keys[i]:vals[i]})
        
        return header
    
    def load_data(self):
        f = open(self.path, 'rb')
        f.seek(self.header['data_starter'] + 2)
        
        raw_data1D = np.fromfile(f, dtype = '>f4', count = -1)
        f.close()
        
        data3D = raw_data1D.reshape((self.header['channels_num'], self.header['xPixels'], self.header['yPixels']))
        for i in range(self.header['channels_num']):
            if i%2 == 1:
                data3D[i, :, :] = data3D[i, :, :][:,::-1] # Reverse column for backward scanning
        if self.header['SCAN_DIR'] == 'up':
            data3D = data3D[:,::-1,:]
        
        return data3D




'''
put the data into a Data Structure
'''

## Data structure of 3ds file
class Data3dsStru():
    
    def __init__(self, path):
        lData = Load3ds(path)
        self.header = lData.header
        self.data3D = lData.data3D
        self.name = path.split('.')[-2].split('/')[-1]
    
    # return the number n layer dIdV data
    def get_dIdV_data(self, n = 0):
        '''
        n is the nth layer dI/dV data with the default is 0.
        If n is 0 or default, return the dI/dV data for all layers of differents energies. 
        If n < points & n > 0, return the dI/dV data corresponding to the nth layer energy.    

        '''
        points = self.header['points']
        # which channels is not decided yet
        if 'LI Demod 1 X (A)' in self.header['channels']:
            dIdV_channel_index = self.header['channels'].index('LI Demod 1 X (A)')
        elif 'Input 2 (V)' in self.header['channels']:
            dIdV_channel_index = self.header['channels'].index('Input 2 (V)')
        par_num = self.header['# parameters (4 byte)']
        
        # data start index
        index = par_num + dIdV_channel_index * points
        
        if n == 0:
            dIdV = self.data3D[index:index+points, :, :] * 1e10
        elif (n > points) | (n < 0):
            raise Exception('wrong number, n should >0 and <={}'.format(points))
        else:
            dIdV = self.data3D[index + n - 1, :, :] * 1e10
            
        ###
        uds_dIdV = UdsDataStru3D(dIdV, 'uds3D_'+self.name+'_dIdV')
        
        sweepSgnUnit = self.header['sweep signal'].split('(')[-1].split(')')[0]
        layer_value_start = 0
        layer_value_stop = 0
        layer_value_interval = 0
        uds_var_layer_value = []
        if sweepSgnUnit == 'V':
            uds_dIdV.info['LayerSignal'] = self.header['sweep signal'].split('(')[0]+'(mV)'
            layer_value_start = int(self.data3D[0,0,0] * 1e6) / 1e3
            layer_value_stop = int(self.data3D[1,0,0] * 1e6) / 1e3
        else:
            uds_dIdV.info['LayerSignal'] = self.header['sweep signal']
            layer_value_start = int(self.data3D[0,0,0] * 1e3) / 1e3
            layer_value_stop = int(self.data3D[1,0,0] * 1e3) / 1e3
                    
        if uds_dIdV.data.shape[0] > 1:
            layer_value_interval = (layer_value_stop - layer_value_start) / (uds_dIdV.data.shape[0]-1)
            for i in range(uds_dIdV.data.shape[0]):
                layer_value = int( (layer_value_start + i * layer_value_interval) * 1e3 ) / 1e3
                uds_var_layer_value.append(layer_value)
        else:
            layer_value = int( (layer_value_start + (n-1) * layer_value_interval) * 1e3 ) / 1e3
            uds_var_layer_value.append(layer_value)
            
        uds_dIdV.info['LayerValue'] = uds_var_layer_value
            
        return uds_dIdV
    
    def get_Topo(self):
        '''
        return the Z value of each point in the grid when mapping.
    
        '''
        fixed_par_num = len(self.header['fixed parameters'])
        
        # whether Z, Z offset, Final Z or scan Z is the real topo is not decided
        Z_index = self.header['experiment parameters'].index('Scan:Z (m)')
        
        index = fixed_par_num + Z_index
        
        Topo = self.data3D[index, :, :] * 1e10
        
        ###
        uds_Topo = UdsDataStru3D(Topo[np.newaxis,:,:], 'uds3D_' + self.name+'_Topo')
        
        uds_Topo.info['LayerValue'] = ['?']
        
        return uds_Topo
    
    def get_Phase(self):
        '''
        phase = arctan(LI Demod 1 Y (A)/LI Demod 1 X (A))
        '''
        points = self.header['points']
        dIdV_X_channel_index = self.header['channels'].index('LI Demod 1 X (A)')
        dIdV_Y_channel_index = self.header['channels'].index('LI Demod 1 Y (A)')
        par_num = self.header['# parameters (4 byte)']
        X_index = par_num + dIdV_X_channel_index * points
        Y_index = par_num + dIdV_Y_channel_index * points
        dIdV_X = self.data3D[X_index : X_index+points, :, :]
        dIdV_Y = self.data3D[Y_index : Y_index+points, :, :]
        tan_theta = dIdV_Y/dIdV_X
        phase = np.arctan(tan_theta)
        
        uds_Phase = UdsDataStru3D(phase, 'uds3D_'+self.name+'_Phase')

        return uds_Phase



## Data structure of sxm file
class DataSxmStru():
    
    def __init__(self, path):
        lData = LoadSxm(path)
        self.header = lData.header
        self.data3D = lData.data3D
        self.name = path.split('.')[-2].split('/')[-1]
        
    def get_Topo_fwd(self):
        
        index = self.header['channels'].index('Z')
        Topo_fwd = self.data3D[index, :, :]* 1e10
        
        ###
        uds_Topo_fwd = UdsDataStru3D(Topo_fwd[np.newaxis,:,:], 'uds3D_'+self.name+'_Topo_fwd')
        
        uds_Topo_fwd.info['LayerValue'] = ['?']
        
        return uds_Topo_fwd
    
    
    def get_Topo_bwd(self):
        
        index = self.header['channels'].index('Z')
        if self.header['DATA_INFO'][index][3] == 'both':
            Topo_bwd = self.data3D[index+1, :, :]* 1e10
        else:
            Topo_bwd = np.zeros(self.header['xPixels'],self.header['yPixels'])
        
        ###
        uds_Topo_bwd = UdsDataStru3D(Topo_bwd[np.newaxis,:,:], 'uds3D_'+self.name+'_Topo_bwd')
        
        uds_Topo_bwd.info['LayerValue'] = ['?']
        
        return uds_Topo_bwd
    
    
    def get_dIdV_fwd(self):
        
        index = self.header['channels'].index('LI_Demod_1_X')
        dIdV_fwd = self.data3D[index*2, :, :]* 1e10
        
        ###
        uds_dIdV_fwd = UdsDataStru3D(dIdV_fwd[np.newaxis,:,:], 'uds3D_'+self.name+'_dIdV_fwd')
        
        uds_dIdV_fwd.info['LayerValue'] = ['?']
        
        return uds_dIdV_fwd
    
    
    def get_dIdV_bwd(self):
        
        index = self.header['channels'].index('LI_Demod_1_X')
        if self.header['DATA_INFO'][index][3] == 'both':
            dIdV_bwd = self.data3D[index*2 + 1, :, :]* 1e10
        else:
            dIdV_bwd = np.zeros(self.header['xPixels'],self.header['yPixels'])
        
        ###
        uds_dIdV_bwd = UdsDataStru3D(dIdV_bwd[np.newaxis,:,:], 'uds3D_'+self.name+'_dIdV_bwd')
        
        uds_dIdV_bwd.info['LayerValue'] = ['?']
        
        return uds_dIdV_bwd
    
    def get_Current_fwd(self):
        
        if 'Current' in self.header['channels']:
            index = self.header['channels'].index('Current')
            Current_fwd = self.data3D[index*2, :, :]* 1e10
        else:
            Current_fwd = np.zeros(self.header['xPixels'],self.header['yPixels'])
        
        ###
        uds_Current_fwd = UdsDataStru3D(Current_fwd[np.newaxis,:,:], 'uds3D_'+self.name+'_Current_fwd')
        
        uds_Current_fwd.info['LayerValue'] = ['?']
        
        return uds_Current_fwd
    
    def get_Current_bwd(self):
        
        if 'Current' in self.header['channels']:
            index = self.header['channels'].index('Current')
            if self.header['DATA_INFO'][index][3] == 'both':
                Current_bwd = self.data3D[index*2 + 1, :, :]* 1e10
        else:
            Current_bwd = np.zeros(self.header['xPixels'],self.header['yPixels'])
        
        ###
        uds_Current_bwd = UdsDataStru3D(Current_bwd[np.newaxis,:,:], 'uds3D_'+self.name+'_Current_bwd')
        
        uds_Current_bwd.info['LayerValue'] = ['?']
        
        return uds_Current_bwd




        
        