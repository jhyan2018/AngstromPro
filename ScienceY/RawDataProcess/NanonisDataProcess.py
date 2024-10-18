'''
Load the Nanonis 3ds file data into dict named header and a 3D array named data3D.
Get the dI/dV map and Topo form the data3D
@author: Huiyu Zhao, Jiahao Yan
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

## Load sxm file
class LoadDat():
    
    def __init__(self, path):
        self.path = path
        self.header = self.get_header()
        self.data2D = self.load_data()
    
    def get_header(self):
        f =open(self.path, 'rb')
        
        header = {}
        while 1:
            Line = f.readline().decode().strip()
            if Line == '':
                Line = f.readline().decode().strip()
            if '[DATA]' == Line :
                data_content = f.readline().decode().strip()
                data_starter = f.tell()
                break
            line1 = Line.split('\t')
            s_key = line1[0]
            if len(line1) < 2:
                s_val = ' '
            else:
                s_val = line1[-1]
            header.update({s_key : s_val})
        f.close()
        header.update({'data starter' : data_starter})
        header.update({'data content' : data_content})
        return header
    
    def load_data(self):
        f = open(self.path, 'rb')
        f.seek(self.header['data starter'], 0)
        data = np.loadtxt( f, dtype = np.float64, encoding = 'utf-8')
        return data

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
        self.channel_dict['X'] = ['X (m)']
        self.channel_dict['Y'] = ['Y (m)']
        
    def append_channel_dict(self, key, value):
        if key in self.channel_dict:
            self.channel_dict[key].append(value)
        else:
            print("Unknown key in channel dict!")
    
    def get_axis_name(self, isDimension3=True):
        axis_name_list = []
        
        if isDimension3:
            axis_name_list.append(self.header['sweep signal'])
            axis_name_list.append('X (m)')
            axis_name_list.append('Y (m)')
        else:
            axis_name_list.append('XY (m)')
            axis_name_list.append(self.header['sweep signal'])
        
        return axis_name_list
    
    def get_axis_value(self, channel, isDimension3=True):
        axis_value_list = []
        
        bias_points = self.header['points']
        Sweep_start_index = self.header['fixed parameters'].index('Sweep Start')
        Sweep_end_index = self.header['fixed parameters'].index('Sweep End')
        bias_raster = np.linspace(self.data3D[Sweep_start_index, 0, 0], self.data3D[Sweep_end_index, 0, 0], bias_points)
        
        if isDimension3:
            axis_value_list.append(bias_raster.tolist())
            
            x_width = self.header['grid settings']['W']
            y_height = self.header['grid settings']['H']
            x_points = self.header['grid dim'][1]
            y_points = self.header['grid dim'][0]
            
            xx = np.linspace(0,x_width, x_points)
            yy = np.linspace(0,y_height, y_points)
            axis_value_list.append(xx.tolist())
            axis_value_list.append(yy.tolist())
        else:
            xx = self.extract_data_layers('X')
            yy = self.extract_data_layers('Y')
            xx_reshape = xx.reshape((xx.shape[0] * xx.shape[1]))
            yy_reshape = yy.reshape((yy.shape[0] * yy.shape[1]))

            xy = np.zeros((xx.shape[0],2))
            xy[:,0]=xx_reshape
            xy[:,1]=yy_reshape            
            axis_value_list.append(xy.tolist()) # reversed
            if channel == 'Topo':
                if 'bias>bias (v)' in self.header.keys():
                    bias_sp = [self.header['bias>bias (v)']]
                else:
                    bias_sp = [0]
                axis_value_list.append(bias_sp)
            else:
                axis_value_list.append(bias_raster.tolist())
        return axis_value_list
    
    def setDataInfo(self, uds_data, channel, single_layer=True):
        info = uds_data.info
        
        if 'current>current (a)' in self.header.keys():
            current = NumberExpression.float_to_simplified_number(self.header['current>current (a)'])
            info['Current Setpoint(A)'] = current
        if 'bias>bias (v)' in self.header.keys():
            bias = NumberExpression.float_to_simplified_number(self.header['bias>bias (v)'])
            info['Bias Setpoint(V)'] =  bias
        if not single_layer:
            info['LayerSignal'] = self.header['sweep signal']            
            layer_value_list = []
            layer_idx =  uds_data.axis_name.index('Bias (V)')
            for a_v in uds_data.axis_value[layer_idx]:
                layer_value_list.append(NumberExpression.float_to_simplified_number(a_v))
            separator = ',' 
            info['LayerValue'] = separator.join(layer_value_list)
        else:
            if 'bias>bias (v)' in self.header.keys():
                bias = NumberExpression.float_to_simplified_number(self.header['bias>bias (v)'])
                info['LayerValue'] = bias
            else:
                info['LayerValue'] = '0'
                
        # info - channel
        if channel == 'dIdV':
            info['Channel'] = 'dI/dV Map'
            info['Data_Name_Unit'] = 'dI/dV (S)'
        elif channel == 'Topo':
            info['Channel'] = 'Topo'
            info['Data_Name_Unit'] = 'Z (m)'
        elif channel == 'Current':
            info['Channel'] = 'Current Map'
            info['Data_Name_Unit'] = 'Current (A)'
        elif channel == 'Phase':
            info['Channel'] = 'dI/dV Phase Map'
            info['Data_Name_Unit'] = 'Phase (rad)'
        else:
            pass
    
    # extract data
    def extract_data_layers(self, channel, param_type='Fixed'):
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
                
        return extrated_data
    
    def extractData(self, channel, param_type='Fixed'):
        extrated_data = self.extract_data_layers(channel, param_type)
        ###
        isDimension3=True
        if extrated_data.shape[-1] == 1:
            if channel == 'Topo':
                extrated_data_reshape = extrated_data.reshape((extrated_data.shape[1], extrated_data.shape[0]))
            else:
                extrated_data_reshape = extrated_data.reshape((extrated_data.shape[0], extrated_data.shape[1]))
                
            extrated_data_transpose = extrated_data_reshape.transpose()
            uds_data = UdsDataStru(extrated_data_transpose, 'uds2D_'+self.name+'_'+channel)
            isDimension3=False
        else:
            if param_type == 'Fixed':
                uds_data = UdsDataStru(extrated_data[np.newaxis,:,:], 'uds3D_'+self.name+'_'+channel)
            else:
                uds_data = UdsDataStru(extrated_data, 'uds3D_'+self.name+'_'+channel)
        
        # axis name & value
        uds_data.axis_name = self.get_axis_name(isDimension3)
        uds_data.axis_value = self.get_axis_value(channel, isDimension3)
        
        # info
        if param_type == 'Fixed':
            self.setDataInfo(uds_data, channel)
        else:
            self.setDataInfo(uds_data, channel, False)
                
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
        uds_dIdV = self.extractData('dIdV','NonFixed') 
        uds_dIdV.data = uds_dIdV.data / lockInAmp
        
        #        
        return uds_dIdV    
    
    def get_Topo(self):
        #
        uds_Topo = self.extractData('Topo')
        
        return uds_Topo
    
    def get_Phase(self):
        #phase = arctan(LI Demod 1 Y (A)/LI Demod 1 X (A))
        uds_dIdV_X = self.extractData('dIdV','NonFixed')
        uds_dIdV_Phase = self.extractData('Phase','NonFixed')
        if uds_dIdV_X.data.shape == uds_dIdV_Phase.data.shape:
            uds_dIdV_Phase.data = np.arctan2(uds_dIdV_Phase.data, uds_dIdV_X.data)            
        
        return uds_dIdV_Phase
    
    def get_Current(self):
        #
        uds_Current = self.extractData('Current','NonFixed') 
                
        return uds_Current

## Data structure of sxm file
class DataSxmStru():
    
    def __init__(self, path, name):
        lData = LoadSxm(path)
        self.header = lData.header
        self.data3D = lData.data3D
        self.name = name
        self.channel_dict = dict()
        self.channel_dict['dIdV'] = ['LI_Demod_1_X']
        self.channel_dict['Topo'] = ['Z']
        self.channel_dict['Current'] = ['Current']
        self.channel_dict['Phase'] = ['LI_Demod_1_Y']
        
    def setDataInfo(self, uds_data, channel):
        info = uds_data.info
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
        
        # info - scan range
        scan_range = self.header['SCAN_RANGE'].split(' ')
        scan_offset = self.header['SCAN_OFFSET'].split(' ')
        scan_angle = self.header['SCAN_ANGLE']
        FOV= [scan_range[0], scan_range[-1], scan_offset[0], scan_offset[-1], scan_angle]
        separator = ','
        info['FOV'] = separator.join(FOV)
        
        # info - channel
        if channel == 'dIdV':
            info['Channel'] = 'dI/dV Map'
        elif channel == 'Topo':
            info['Channel'] = 'Topo'
        elif channel == 'Current':
            info['Channel'] = 'Current Map'
        elif channel == 'Phase':
            info['Channel'] = 'dI/dV Phase Map'
        else:
            pass    
    #
    def extractData(self, channel, direction='fwd'):
        #
        index_offset = 0
        if direction == 'fwd':
            pass
        elif direction == 'bwd':
            index_offset = 1
        else:
            print('Unknow scan direction!')
            
        #
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
            extrated_data = self.data3D[channel_index*2+index_offset, :, :]
        
        #
        uds_data=UdsDataStru(extrated_data[np.newaxis,:,:], 'uds3D_'+self.name+'_'+channel+'_'+direction)
        
        # info
        self.setDataInfo(uds_data, channel)
        
        # axis_name
        uds_data.axis_name = ['X (m)', 'Y (m)']
        
        # axis_value
        x_width = float(uds_data.info['FOV'].split(',')[0])
        y_height = float(uds_data.info['FOV'].split(',')[1])
        x_points = self.header['xPixels']
        y_points = self.header['yPixels']
            
        xx = np.linspace(0,x_width, x_points)
        yy = np.linspace(0,y_height, y_points)
        uds_data.axis_value.append(xx.tolist())
        uds_data.axis_value.append(yy.tolist())
        
        return uds_data        
        
    def get_Topo_fwd(self):
        uds_Topo_fwd = self.extractData('Topo')
        
        return uds_Topo_fwd  
    
    def get_dIdV_fwd(self):
        uds_dIdV_fwd = self.extractData('dIdV')
        if 'Lock-in>Amplitude' in self.header.keys():
            lockInAmp = self.header['Lock-in>Amplitude']
            if self.header['Lock-in>Modulated signal'] == 'Bias (V)':
                uds_dIdV_fwd.data = uds_dIdV_fwd.data / lockInAmp
        
        return uds_dIdV_fwd
    
    def get_theta_fwd(self):
        uds_dIdV_Phase = self.extractData('Phase')
        uds_dIdV_X = self.extractData('dIdV')
        if uds_dIdV_X.data.shape == uds_dIdV_Phase.data.shape:
            uds_dIdV_Phase.data = np.arctan2(uds_dIdV_Phase.data, uds_dIdV_X.data)
        
        return uds_dIdV_Phase    
    
    def get_Current_fwd(self):
        uds_Current_fwd = self.extractData('Current')
        
        return uds_Current_fwd
    
## Data structure of sxm file
class DataDatStru():
    
    def __init__(self, path, name):
        lData = LoadDat(path)
        self.header = lData.header
        self.data2D = lData.data2D
        self.name = name
        self.channel_dict = dict()
        if self.header['Experiment'] == 'bias spectroscopy':
            self.channel_dict['dIdV'] = ['LI Demod 1 X (A)']
            self.channel_dict['Current'] = ['Current (A)']
            self.channel_dict['Phase'] = ['LI Demod 1 Y (A)']
        elif self.header['Experiment'] == 'Z spectroscopy':
            self.channel_dict['I-Z'] = ['Current (A)']
            self.channel_dict['I-Z bwd'] = ['Current [bwd] (A)']
        else:
            pass
    
    def append_channel_dict(self, key, value):
        if key in self.channel_dict:
            self.channel_dict[key].append(value)
        else:
            print("Unknown key in channel dict!")
    
    def get_axis_name(self):
        axis_name_list = []
        axis_name_list.append('XY (m)')
        axis_name_list.append(self.header['data content'].split('\t')[0])
                
        return axis_name_list
    
    def get_axis_value(self):
        axis_value_list = []
        
        x_pos = float(self.header['X (m)'])
        y_pos = float(self.header['Y (m)'])
        axis_value_list.append([[x_pos, y_pos]])
        
        av_ = self.data2D[:, 0]
        axis_value_list.append(av_.tolist())
        
        return axis_value_list
            
    def setDataInfo(self, uds_data, channel):
        info = uds_data.info
        if 'Current>Current (A)' in self.header.keys():
            current = NumberExpression.float_to_simplified_number(float(self.header['Current>Current (A)']))
            info['Current Setpoint(A)'] = current
        if 'Bias>Bias (V)' in self.header.keys():
            bias = NumberExpression.float_to_simplified_number(float(self.header['Bias>Bias (V)']))
            info['Bias Setpoint(V)'] = bias
        
        # info - channel
        if channel == 'dIdV':
            info['Channel'] = 'dI/dV Curve'
            info['Data_Name_Unit'] = 'dI/dV (S)'
        elif channel == 'Current':
            info['Channel'] = 'I(V) Curve'
            info['Data_Name_Unit'] = 'Current (A)'
        elif channel == 'Phase':
            info['Channel'] = 'dI/dV Phase Curve'
            info['Data_Name_Unit'] = 'Phase (rad)'
        elif channel == 'I-Z':
            info['Channel'] = 'I(Z) Curve'
            info['Data_Name_Unit'] = 'Current (A)'
        else:
            pass 
    
    def extractData(self, channel):
        ch_cnt = 0
        channel_index = 0
        for ch in self.channel_dict[channel]:
            if ch in self.header['data content'].split('\t'):
                channel_index = self.header['data content'].split('\t').index(ch)
                break
            ch_cnt += 1            
        if ch_cnt == len(self.channel_dict[channel]):
            extrated_data_reshape = np.ones((1,100))
        else:          
            extrated_data = self.data2D[:, channel_index]
            extrated_data_reshape = extrated_data.reshape((1,len(extrated_data)))
        
        uds_data = UdsDataStru(extrated_data_reshape, 'uds2D_'+self.name+'_'+channel)
        
        # axis name & value
        uds_data.axis_name = self.get_axis_name()
        uds_data.axis_value = self.get_axis_value()
        
        # info
        self.setDataInfo(uds_data, channel)
        
        return uds_data
         
    def get_dIdV(self):
        uds_dIdV = self.extractData('dIdV')
        if 'Lock-in>Amplitude' in self.header.keys():
            lockInAmp = float(self.header['Lock-in>Amplitude'])
            if self.header['Lock-in>Modulated signal'] == 'Bias (V)':
                uds_dIdV.data = uds_dIdV.data / lockInAmp
        
        return uds_dIdV
    
    def get_theta(self):
        uds_dIdV_Phase = self.extractData('Phase')
        uds_dIdV_X = self.extractData('dIdV')
        if uds_dIdV_X.data.shape == uds_dIdV_Phase.data.shape:
            uds_dIdV_Phase.data = np.arctan2(uds_dIdV_Phase.data, uds_dIdV_X.data)
        
        return uds_dIdV_Phase
    
    def get_Current(self):
        uds_Current = self.extractData('Current')
        
        return uds_Current
    
    def get_I_Z(self):
        uds_I_Z = self.extractData('I-Z')
        
        return uds_I_Z
    
    def get_I_Z_bwd(self):
        uds_I_Z_bwd = self.extractData('I-Z bwd')
        
        return uds_I_Z_bwd