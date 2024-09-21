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
from .UdsDataProcess import UdsDataStru
from ..GUI.general.NumberExpression import NumberExpression
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
        if 'lock-in>amplitude' in header.keys():
            header['lock-in>amplitude'] = float(header['lock-in>amplitude'])
        if 'bias>bias (v)' in header.keys():
            header['bias>bias (v)'] = float(header['bias>bias (v)'])
        if 'current>current (a)' in header.keys():
            header['current>current (a)'] = float(header['current>current (a)'])
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
        
        data2D = raw_data1D.astype('f4').reshape((-1, l))
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
        lines.pop(0) # remove the fist line: Channel Name Unit Direction Calibration Offset
        channels = []
        channels_num = 0
        channels_dir = []
        for line in lines:
            val = line.split()
            if len(val) > 1:
                header['DATA_INFO'].append(val)
                channels.append(val[1])
                channels_dir.append(val[3])
                if val[3] != 'both':
                    print ('warning, only one direction recorded, expect a crash :D', val)
                    channels_num += 1
                else:
                    channels_num += 2
        header.update({'channels': channels})
        header.update({'channels_num': channels_num})
        header.update({'channels_dir': channels_dir})
        
        xPixels, yPixels = header['SCAN_PIXELS'].split()
        xPixels = int(xPixels)
        yPixels = int(yPixels)
        header.update({'xPixels': xPixels})
        header.update({'yPixels': yPixels})
        if 'Lock-in>Amplitude' in header.keys():
            header['Lock-in>Amplitude'] = float(header['Lock-in>Amplitude'])
        if 'BIAS' in header.keys():
            header['BIAS'] = float(header['BIAS'])
        if 'Current>Current (A)'in header.keys():
            header['Current>Current (A)'] = float(header['Current>Current (A)'])
        if 'Z-CONTROLLER' in header.keys():
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
        
        data3D = raw_data1D.astype('f4').reshape((self.header['channels_num'], self.header['xPixels'], self.header['yPixels']))
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
    
    def __init__(self, path, name):
        lData = Load3ds(path)
        self.header = lData.header
        self.data3D = lData.data3D
        self.name = name
        self.channel_dict = dict()
        self.channel_dict['dIdV'] = ['LI Demod 1 X (A)', 'Input 2 (V)']
        self.channel_dict['Topo'] = ['Scan:Z (m)']
        self.channel_dict['Current'] = ['Current (A)']
        self.channel_dict['Phase'] = ['LI Demod 1 Y (A)']
        self.layerValue = self.get_Layer_Value()
        
    def append_channel_dict(self, key, value):
        if key in self.channel_dict:
            self.channel_dict[key].append(value)
        else:
            print("Unknown key in channel dict!")
        
    def get_Layer_Value(self):
        points = self.header['points']
        Sweep_start_index = self.header['fixed parameters'].index('Sweep Start')
        Sweep_end_index = self.header['fixed parameters'].index('Sweep End')
        layer_value_list = []
        
        for i in range(points):
            value = (self.data3D[Sweep_end_index, 0, 0] - self.data3D[Sweep_start_index, 0, 0]) / (points - 1) * i + self.data3D[Sweep_start_index, 0, 0]
            layer_value_list.append(NumberExpression.float_to_simplified_number(value))
        separator = ','
        layer_value = separator.join(layer_value_list)
        
        return layer_value
    
    def get_axis_name(self, isDimension3=True):
        axis_name_list = []
        if isDimension3:
            axis_name_list.append('X (m)')
            axis_name_list.append('Y (m)')
        else:
            axis_name_list.append('XY (m)')
        axis_name_list.append(self.header['sweep signal'])
        
        separator = ','
        axis_name = separator.join(axis_name_list)
        
        return axis_name
    
    def get_axis_value(self, isDimension3=True):
        axis_value_list = []
        if isDimension3:
            x_width = self.header['grid settings']['W']
            y_height = self.header['grid settings']['H']
            x_points = self.header['grid dim'][1]
            y_points = self.header['grid dim'][0]
            
            bias_points = self.header['points']
            Sweep_start_index = self.header['fixed parameters'].index('Sweep Start')
            Sweep_end_index = self.header['fixed parameters'].index('Sweep End')
            bias_raster = np.linspace(self.data3D[Sweep_start_index, 0, 0], self.data3D[Sweep_end_index, 0, 0], bias_points)
            
            xx = np.linspace(0,x_width, x_points)
            yy = np.linspace(0,y_height, y_points)
            axis_value_list.append(xx.tolist())
            axis_value_list.append(yy.tolist())
            axis_value_list.append(bias_raster.tolist())
        else:
            pass
        
        return axis_value_list
    
    def setDataInfo(self, single_layer=True):
        info = dict()       
        
        if 'current>current (a)' in self.header.keys():
            current = NumberExpression.float_to_simplified_number(self.header['current>current (a)'])
            info['Current Setpoint(A)'] = current
        if 'bias>bias (v)' in self.header.keys():
            bias = NumberExpression.float_to_simplified_number(self.header['bias>bias (v)'])
            info['Bias Setpoint(V)'] =  bias
        if not single_layer:
            info['LayerSignal'] = self.header['sweep signal']
            info['LayerValue'] = self.layerValue
        else:
            if 'bias>bias (v)' in self.header.keys():
                bias = NumberExpression.float_to_simplified_number(self.header['bias>bias (v)'])
                info['LayerValue'] = bias
            else:
                info['LayerValue'] = '0'
        
        return info
    
    # extract data
    def extract_data(self, channel, param_type='Fixed'):
        #
        index = 0
        if param_type == 'Fixed':
            fixed_par_num = len(self.header['fixed parameters'])
            channel_index = self.header['experiment parameters'].index(self.channel_dict[channel][0])            
            index = fixed_par_num + channel_index          
            extrated_data = self.data3D[index, :, :]
        else:
            ch_cnt = 0
            channel_index = 0
            for ch in self.channel_dict[channel]:
                if ch in self.header['channels']:
                    channel_index = self.header['channels'].index(ch)
                    break
                ch_cnt += 1            
            if ch_cnt == len(self.channel_dict[channel]):
                extrated_data = np.ones((1,100,100))
            else:
                par_num = self.header['# parameters (4 byte)']
                points = self.header['points']            
                index = par_num + channel_index * points           
                extrated_data = self.data3D[index:index+points, :, :]
                
        ###
        isDimension3=True
        if extrated_data.shape[-1] == 1:
            extrated_data_reshape = extrated_data.reshape((extrated_data.shape[0], extrated_data.shape[1]))
            extrated_data_transpose = extrated_data_reshape.transpose()
            uds_data = UdsDataStru(extrated_data_transpose, 'uds2D_'+self.name+'_'+channel)
            isDimension3=False
        else:
            if param_type == 'Fixed':
                uds_data = UdsDataStru(extrated_data[np.newaxis,:,:], 'uds3D_'+self.name+'_'+channel)
            else:
                uds_data = UdsDataStru(extrated_data, 'uds3D_'+self.name+'_'+channel)
            
        # info - basic
        if param_type == 'Fixed':
            uds_data.info = self.setDataInfo()
        else:
            uds_data.info = self.setDataInfo(False)
        
        # info - channel
        if channel == 'dIdV':
            uds_data.info['Channel'] = 'dI/dV Map'
        elif channel == 'Topo':
            uds_data.info['Channel'] = 'Topo'
        else:
            pass
        
        # axis name & value
        uds_data.axis_name = self.get_axis_name(isDimension3)
        uds_data.axis_value = self.get_axis_value(isDimension3)
                
        return uds_data
        
    # return the number n layer dIdV data
    def get_dIdV_data(self):
        #
        if 'lock-in>amplitude' in self.header.keys():
            if self.header['lock-in>modulated signal'] == 'Bias (V)':
                lockInAmp = self.header['lock-in>amplitude']
        else:
            lockInAmp = 1
        
        #
        uds_dIdV = self.extract_data('dIdV','NonFixed') 
        uds_dIdV.data = uds_dIdV.data / lockInAmp
        
        #        
        return uds_dIdV    
    
    def get_Topo(self):
        #
        uds_Topo = self.extract_data('Topo')
        
        return uds_Topo
    
    def get_Phase(self):
        #phase = arctan(LI Demod 1 Y (A)/LI Demod 1 X (A))
        uds_dIdV_X = self.extract_data('dIdV','NonFixed')
        uds_dIdV_Phase = self.extract_data('Phase','NonFixed')
        uds_dIdV_Phase.data = np.arctan2(uds_dIdV_Phase.data, uds_dIdV_X.data)
        
        return uds_dIdV_Phase
    
    def get_Current(self):
        #
        uds_Current = self.extract_data('Current','NonFixed') 
                
        return uds_Current

## Data structure of sxm file
class DataSxmStru():
    
    def __init__(self, path, name):
        lData = LoadSxm(path)
        self.header = lData.header
        self.data3D = lData.data3D
        self.name = name
        self.channel_list = []
        self.channel_list.append(lData.header['channels']) 
        self.channel_list.append(lData.header['channels_dir'])
        
    def setDataInfo(self):
        info = dict()
        if 'Current>Current (A)' in self.header.keys():
            current = NumberExpression.float_to_simplified_number(self.header['Current>Current (A)'])
            info['Current Setpoint(A)'] = current
        if 'Z-CONTROLLER' in self.header.keys():
            current = self.header['Z-CONTROLLER']['Setpoint']
            info['Current Setpoint(A)'] = current
        if 'BIAS' in self.header.keys():
            bias = NumberExpression.float_to_simplified_number(self.header['BIAS'])
            info['Bias Setpoint(V)'] = bias
        info['LayerValue'] = bias
        
        return info
    
    def get_Topo_fwd(self):
        
        index = self.header['channels'].index('Z')
        Topo_fwd = self.data3D[index, :, :]
        ###
        uds_Topo_fwd = UdsDataStru(Topo_fwd[np.newaxis,:,:], 'uds3D_'+self.name+'_Topo_fwd')
        
        #
        uds_Topo_fwd.info = self.setDataInfo()
        uds_Topo_fwd.info['Channel'] = 'Topo'
        
        return uds_Topo_fwd
    
    
    def get_Topo_bwd(self):
        
        index = self.header['channels'].index('Z')
        if self.header['DATA_INFO'][index][3] == 'both':
            Topo_bwd = self.data3D[index+1, :, :]
        else:
            Topo_bwd = np.zeros(self.header['xPixels'],self.header['yPixels'])
        
        ###
        uds_Topo_bwd = UdsDataStru(Topo_bwd[np.newaxis,:,:], 'uds3D_'+self.name+'_Topo_bwd')
        
        #
        uds_Topo_bwd.info = self.setDataInfo()
        uds_Topo_bwd.info['Channel'] = 'Topo'
        
        return uds_Topo_bwd   
    
    def get_dIdV_fwd(self):
        
        index = self.header['channels'].index('LI_Demod_1_X')
        if 'Lock-in>Amplitude' in self.header.keys():
            lockInAmp = self.header['Lock-in>Amplitude']
            if self.header['Lock-in>Modulated signal'] == 'Bias (V)':
                dIdV_fwd = self.data3D[index*2, :, :]/lockInAmp
        else:
            dIdV_fwd = self.data3D[index*2, :, :]
        
        ###
        uds_dIdV_fwd = UdsDataStru(dIdV_fwd[np.newaxis,:,:], 'uds3D_'+self.name+'_dIdV_fwd')
        
        #
        uds_dIdV_fwd.info = self.setDataInfo()
        uds_dIdV_fwd.info['Channel'] = 'dI/dV Map'
        
        return uds_dIdV_fwd
      
    def get_dIdV_bwd(self):
        
        index = self.header['channels'].index('LI_Demod_1_X')
        if 'Lock-in>Amplitude' in self.header.keys():
            lockInAmp = self.header['Lock-in>Amplitude']
            if (self.header['Lock-in>Modulated signal'] == 'Bias (V)') & (self.header['DATA_INFO'][index][3] == 'both'):
                dIdV_bwd = self.data3D[index*2 + 1, :, :]/lockInAmp
            else:
                dIdV_bwd = np.zeros(self.header['xPixels'],self.header['yPixels'])
        else:
            dIdV_bwd = self.data3D[index*2 + 1, :,:]
        
        ###
        uds_dIdV_bwd = UdsDataStru(dIdV_bwd[np.newaxis,:,:], 'uds3D_'+self.name+'_dIdV_bwd')
        
        #
        uds_dIdV_bwd.info = self.setDataInfo()
        uds_dIdV_bwd.info['Channel'] = 'dI/dV Map'
        
        return uds_dIdV_bwd
      
    def get_dIdV_Y_fwd(self):
        
        index = self.header['channels'].index('LI_Demod_1_Y')
        if 'Lock-in>Amplitude' in self.header.keys():
            lockInAmp = self.header['Lock-in>Amplitude']
            if self.header['Lock-in>Modulated signal'] == 'Bias (V)':
                dIdV_Y_fwd = self.data3D[index*2, :, :]/lockInAmp
        else:
            dIdV_Y_fwd = self.data3D[index*2, :, :]
        
        ###
        uds_dIdV_Y_fwd = UdsDataStru(dIdV_Y_fwd[np.newaxis,:,:], 'uds3D_'+self.name+'_dIdV_Y_fwd')
        
        #
        uds_dIdV_Y_fwd.info = self.setDataInfo()
        uds_dIdV_Y_fwd.info['Channel'] = 'dI/dV Y Map'
        
        return uds_dIdV_Y_fwd  

    def get_dIdV_Y_bwd(self):
        
        index = self.header['channels'].index('LI_Demod_1_Y')
        if 'Lock-in>Amplitude' in self.header.keys():
            lockInAmp = self.header['Lock-in>Amplitude']
            if (self.header['Lock-in>Modulated signal'] == 'Bias (V)') & (self.header['DATA_INFO'][index][3] == 'both'):
                dIdV_Y_bwd = self.data3D[index*2 + 1, :, :]/lockInAmp
            else:
                dIdV_Y_bwd = np.zeros(self.header['xPixels'],self.header['yPixels'])
        else:
            dIdV_Y_bwd = self.data3D[index*2 + 1, :, :]
        
        ###
        uds_dIdV_Y_bwd = UdsDataStru(dIdV_Y_bwd[np.newaxis,:,:], 'uds3D_'+self.name+'_dIdV_Y_bwd')
        
        #
        uds_dIdV_Y_bwd.info = self.setDataInfo()
        uds_dIdV_Y_bwd.info['Channel'] = 'dI/dV Y Map'
        
        return uds_dIdV_Y_bwd    
    
    def get_theta(self):
        
        Yindex = self.header['channels'].index('LI_Demod_1_Y')
        Xindex = self.header['channels'].index('LI_Demod_1_X')
        dIdV_Y = self.data3D[Yindex*2, :, :]
        dIdV_X = self.data3D[Xindex*2, :, :]
        Theta = np.arctan2(dIdV_Y, dIdV_X)
        
        uds_Theta = UdsDataStru(Theta[np.newaxis,:,:], 'uds3D_'+self.name+'_theta')
        
        #
        uds_Theta.info = self.setDataInfo()
        uds_Theta.info['Channel'] = 'dI/dV Phase Map'
        
        return uds_Theta
    
    
    def get_Current_fwd(self):
        
        if 'Current' in self.header['channels']:
            index = self.header['channels'].index('Current')
            Current_fwd = self.data3D[index*2, :, :]
        else:
            Current_fwd = np.zeros(self.header['xPixels'],self.header['yPixels'])
        
        ###
        uds_Current_fwd = UdsDataStru(Current_fwd[np.newaxis,:,:], 'uds3D_'+self.name+'_Current_fwd')
        
        #
        uds_Current_fwd.info = self.setDataInfo()
        uds_Current_fwd.info['Channel'] = 'Current Map'
        
        return uds_Current_fwd
    
    def get_Current_bwd(self):
        
        if 'Current' in self.header['channels']:
            index = self.header['channels'].index('Current')
            if self.header['DATA_INFO'][index][3] == 'both':
                Current_bwd = self.data3D[index*2 + 1, :, :]
        else:
            Current_bwd = np.zeros(self.header['xPixels'],self.header['yPixels'])
        
        ###
        uds_Current_bwd = UdsDataStru(Current_bwd[np.newaxis,:,:], 'uds3D_'+self.name+'_Current_bwd')
        
        #
        uds_Current_bwd.info = self.setDataInfo()
        uds_Current_bwd.info['Channel'] = 'Current Map'
        
        return uds_Current_bwd




        
        