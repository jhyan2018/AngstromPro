# -*- coding: utf-8 -*-
"""
Created on Sat May  4 21:38:56 2024

@author: jiahaoYan
"""

"""
System modules
"""
import os
import json
import uuid
from io import BytesIO

"""
Third-party Modules
"""
from PyQt5 import QtGui, QtWidgets
"""
User Modules
"""
from ..GUI.Image2Uds3Widget import Image2Uds3Widget
from ..GUI.Plot1Uds2Widget import Plot1Uds2Widget
from ..RawDataProcess import NanonisDataProcess, LFDataProcess, UdsDataProcess
from ..ImageProcess import ImgProc
from ..GUI.general.NumberExpression import NumberExpression
"""
Local Module Definition
"""
class SnapshotInfo():
    def __init__(self, src_file_path, src_file_lastmodified):
        self.src_file_path = src_file_path
        self.src_file_lastmodified = src_file_lastmodified
        self.src_file_uuid = ''
        self.channel = []
        self.ch_uuid = []
        self.ch_type = []
        self.ch_layers = []
        self.ch_layer_value = []
        self.ch_layer_scale = []
        self.ch_star = []
        self.pixmap = []
        
        self.pivotal_info = []
        self.full_info = []

class SnapshotManager:
    def __init__(self, snapshots_root_dir, settings):
        self.snapshots_root_dir = snapshots_root_dir
        self.metadata_dir = os.path.join(snapshots_root_dir, 'metadata')
        self.snapshots_dir = os.path.join(snapshots_root_dir, 'png')        

        if not os.path.exists(self.snapshots_root_dir):
            os.makedirs(self.snapshots_root_dir)
        if not os.path.exists(self.metadata_dir):
            os.makedirs(self.metadata_dir)
        if not os.path.exists(self.snapshots_dir):
            os.makedirs(self.snapshots_dir)                   
            
        self.metadata_srcfile = os.path.join(snapshots_root_dir, "metadata_srcfile.json")  
        self.snapshots_srcfile = {}

        self.load_metadata_srcfile()
        
        #
        self.settings = settings
        
        #
        self.snapshots_render_image = Image2Uds3Widget()
        self.snapshots_render_image.setSettings(settings)
        # it's necessary to set canvas size, 
        # otherwise it will have issue with rendering to pixmap
        self.snapshots_render_image.static_canvas.setFixedHeight(256)
        self.snapshots_render_image.static_canvas.setFixedWidth(256)
        
        #
        self.img2u3w_src_file_path = ''
        self.img2u3w_channel = ''
        
        #
        self.snapshots_render_plot = Plot1Uds2Widget()
        self.snapshots_render_plot.static_canvas.setFixedHeight(512)
        self.snapshots_render_plot.static_canvas.setFixedWidth(512)

    def load_metadata_srcfile(self):
        if os.path.exists(self.metadata_srcfile):
            with open(self.metadata_srcfile, "r") as f:
                self.snapshots_srcfile = json.load(f)
        else:
            self.snapshots_srcfile = {}

    def save_metadata_srcfile(self):
        with open(self.metadata_srcfile, "w") as f:
            json.dump(self.snapshots_srcfile, f, indent=4)
    
    def load_metadata_file(self, metadata_file_path):
        metadata = {}
        if os.path.exists(metadata_file_path):
            with open(metadata_file_path, "r") as f:
                metadata = json.load(f)
        
            snapshots_info = SnapshotInfo(metadata['src_file_path'], metadata['src_file_lastmodified'])
            snapshots_info.src_file_uuid = metadata['src_file_uuid']
            snapshots_info.channel = metadata['channel']
            snapshots_info.ch_uuid = metadata['ch_uuid']
            snapshots_info.ch_type = metadata['ch_type']
            snapshots_info.ch_layers = metadata['ch_layers']
            snapshots_info.ch_layer_value = metadata['ch_layer_value']
            snapshots_info.ch_layer_scale = metadata['ch_layer_scale']
            snapshots_info.ch_star = metadata['ch_star']
            snapshots_info.pivotal_info = metadata['pivotal_info']
            snapshots_info.full_info = metadata['full_info']
            
            return snapshots_info
        else:
            return None
    
    def save_metadata_file(self, snapshots_info):
        metadata = {}
        
        metadata['src_file_path'] = snapshots_info.src_file_path
        metadata['src_file_lastmodified'] = snapshots_info.src_file_lastmodified
        metadata['src_file_uuid'] = snapshots_info.src_file_uuid
        metadata['channel'] = snapshots_info.channel
        metadata['ch_uuid'] = snapshots_info.ch_uuid
        metadata['ch_type'] = snapshots_info.ch_type
        metadata['ch_layers'] = snapshots_info.ch_layers
        metadata['ch_layer_value'] = snapshots_info.ch_layer_value
        metadata['ch_layer_scale'] = snapshots_info.ch_layer_scale
        metadata['ch_star'] = snapshots_info.ch_star
        metadata['pivotal_info'] = snapshots_info.pivotal_info
        metadata['full_info'] = snapshots_info.full_info
        
        metadata_path = os.path.join(self.metadata_dir, snapshots_info.src_file_uuid)    
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)
        
    def get_snapshots_info(self, srcfile_path, srcfile_lastmodified):
        info = self.snapshots_srcfile.get(srcfile_path, None)
        
        if info:
            metadata_file = info.split('@')[0]
            snapshot_last_modified = info.split('@')[1]
            
            if snapshot_last_modified == srcfile_lastmodified:
                metadata_file_path = os.path.join(self.metadata_dir, f"{metadata_file}")
                return metadata_file_path
            else:
                return None
        else:
            return None
    
    def save_snapshots(self, snapshot_info):
        pixmap_counts = 0
                
        for index, channel in enumerate(snapshot_info.channel):
            uuid_name = f"{uuid.uuid4()}"
            if int(snapshot_info.ch_layers[index]) == 1:
                png_name = uuid_name + '.png'
                snapshot_info.ch_uuid.append(png_name)
                snapshot_path = os.path.join(self.snapshots_dir, f"{png_name}")
                snapshot_info.pixmap[pixmap_counts].save(snapshot_path)
                pixmap_counts += 1
            elif int(snapshot_info.ch_layers[index]) >= 2:
                png_subfolder_name = uuid_name
                snapshot_info.ch_uuid.append(png_subfolder_name)
                png_subpath = os.path.join(self.snapshots_dir, f"{png_subfolder_name}")
                os.makedirs(png_subpath)
                
                snapshot_path = os.path.join(png_subpath, 'layer0.png')
                snapshot_info.pixmap[pixmap_counts].save(snapshot_path)
                pixmap_counts += 1
            else:
                print('Snapshots: Unsupported channel layers!')       

        self.save_metadata_file(snapshot_info)
        
    def generate_snapshots(self, srcfile_path, src_file_lastmodified, channel=None, layer=0, snapshots_info=None):
        # file suffix/format
        suffix = srcfile_path.split('.')[-1]      
                
        if suffix == '3ds':
            if channel == None:
                self.generate_snapshots_to_metafile_from_3ds(srcfile_path, src_file_lastmodified)
            else:
                self.generate_snapshots_to_gallery_content_from_3ds(srcfile_path, src_file_lastmodified, channel, layer, snapshots_info)
        elif suffix == 'sxm':
            if channel == None:
                self.generate_snapshots_to_metafile_from_sxm(srcfile_path, src_file_lastmodified)
            else:
                pass
        elif suffix == 'dat':
            if channel == None:
                self.generate_snapshots_to_metafile_from_dat(srcfile_path, src_file_lastmodified)
            else:
                pass
        elif suffix == 'TFR':
            self.generate_snapshots_to_metafile_from_TFR(srcfile_path, src_file_lastmodified)
        elif suffix == '1FL':
            self.generate_snapshots_to_metafile_from_1FL(srcfile_path, src_file_lastmodified)
        elif suffix == 'uds':
            if channel == None:
                self.generate_snapshots_to_metafile_from_uds(srcfile_path, src_file_lastmodified)
            else:
                pass
        else:
            print('Generate snapshots error: Unsupported file suffix!') 
            
    """ """
    def set_snapshots_render_image_data(self,uds_data):
        self.snapshots_render_image.setUdsData(uds_data)
        
    def set_snapshots_render_plot_data(self,uds_data):
        self.snapshots_render_plot.setUdsData(uds_data)
    
    def generate_singlelayer_snapshots_Plot1U2Widget(self, snapshot_info):
        # use BytesIo to make sure rendering the whole canvas
        """
        buffer = BytesIO()
        self.snapshots_render_plot.static_canvas.figure.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(buffer.getvalue())
        """
        pixmap = QtGui.QPixmap(self.snapshots_render_plot.static_canvas.size())
        self.snapshots_render_plot.static_canvas.render(pixmap)
        snapshot_info.pixmap.append(pixmap)
        
        snapshot_info.ch_layer_value.append('0')
        snapshot_info.ch_layers.append('1')
    
    def generate_singlelayer_snapshots_Img2U3Widget(self, snapshot_info, layer_index=0):        
        layer_value = self.snapshots_render_image.uds_var_layer_value
        separator = ','
        snapshot_info.ch_layer_value.append(separator.join(layer_value))
        layers = len(layer_value)
        snapshot_info.ch_layers.append(str(layers))
        
        layer_scale = []
           
        self.snapshots_render_image.ui_sb_image_layers.setValue(layer_index)
        self.snapshots_render_image.imageLayerChanged()
            
        pixmap = QtGui.QPixmap(self.snapshots_render_image.static_canvas.size())
        self.snapshots_render_image.static_canvas.render(pixmap)
        snapshot_info.pixmap.append(pixmap)
            
        scale_u_v = self.snapshots_render_image.ui_scale_widget.data_upper_value
        scale_l_v = self.snapshots_render_image.ui_scale_widget.data_lower_value 
        layer_scale.append(NumberExpression.float_to_simplified_number(scale_l_v))
        layer_scale.append(NumberExpression.float_to_simplified_number(scale_u_v))
            
        snapshot_info.ch_layer_scale.append(separator.join(layer_scale))     
        
    """ Generate Snapshots to Gallery Content  """
    def generate_snapshots_to_gallery_content_from_3ds(self, srcfile_path, src_file_lastmodified, channel, layer, snapshots_info):

        
        if srcfile_path == self.img2u3w_src_file_path and channel == self.img2u3w_channel:
            reset_img2u3w_data = False
        else:
            reset_img2u3w_data = True
            
            self.img2u3w_src_file_path = srcfile_path
            self.img2u3w_channel = channel
            srcfile_name = srcfile_path.split('/')[-1].split('.')[0]
            data3ds = NanonisDataProcess.Data3dsStru(srcfile_path, srcfile_name)
        
        if channel == 'Topo':
            snapshots_info.channel.append('Topo')
            snapshots_info.ch_type.append('IMAGE')
            
            if reset_img2u3w_data:
                uds3D_topo = data3ds.get_Topo()
                #background subtract
                uds3D_topo_bg = ImgProc.ipBackgroundSubtract2D(uds3D_topo, 2, 'PerLine')
                self.set_snapshots_render_image_data(uds3D_topo_bg)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshots_info, layer)
        elif channel == 'dI/dV Map':
            snapshots_info.channel.append('dI/dV Map')
            snapshots_info.ch_type.append('IMAGE')
            
            if reset_img2u3w_data:
                uds3D_didv = data3ds.get_dIdV_data()
                self.set_snapshots_render_image_data(uds3D_didv)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshots_info, layer)
        
        elif channel == 'Current Map':
            snapshots_info.channel.append('Current Map')
            snapshots_info.ch_type.append('IMAGE')
            
            if reset_img2u3w_data:
                uds3D_current = data3ds.get_Current()
                self.set_snapshots_render_image_data(uds3D_current)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshots_info, layer)
        
        elif channel == 'dI/dV Phase Map':
            snapshots_info.channel.append('dI/dV Phase Map')
            snapshots_info.ch_type.append('IMAGE')
            
            if reset_img2u3w_data:
                uds3D_didv_phase = data3ds.get_Phase()
                self.set_snapshots_render_image_data(uds3D_didv_phase)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshots_info, layer)
        else:
            print('generate_snapshots_to_gallery_content_from_3ds: Unknown Channel!')

    """ Generate Snapshots to Metafile  """
    def generate_snapshots_to_metafile_from_3ds(self, srcfile_path, src_file_lastmodified):
        srcfile_name = srcfile_path.split('/')[-1].split('.')[0]
        data3ds = NanonisDataProcess.Data3dsStru(srcfile_path, srcfile_name)  
        
        snapshot_info = SnapshotInfo(srcfile_path, src_file_lastmodified)

        if 'Scan:Z (m)' in data3ds.channel_dict['Topo']:
            uds_topo = data3ds.get_Topo()
            
            channel = uds_topo.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('Topo')
            
            if uds_topo.name.split('_')[0] == 'uds3D':
                snapshot_info.ch_type.append('IMAGE')
                #background subtract
                uds3D_topo_bg = ImgProc.ipBackgroundSubtract2D(uds_topo, 2, 'PerLine')
                self.set_snapshots_render_image_data(uds3D_topo_bg)
                self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
            elif uds_topo.name.split('_')[0] == 'uds2D':
                snapshot_info.ch_type.append('PLOT')
                self.set_snapshots_render_plot_data(uds_topo)
                self.generate_singlelayer_snapshots_Plot1U2Widget(snapshot_info)
            else:
                print('Snapmanager: Unknow uds data type')
                    
        if ('LI Demod 1 X (A)' in data3ds.channel_dict['dIdV']) or ('Input 2 (V)' in data3ds.channel_dict['dIdV']): 
            uds_didv = data3ds.get_dIdV_data()
            channel = uds_didv.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('dI/dV Map')
                
            if uds_didv.name.split('_')[0] == 'uds3D':
                snapshot_info.ch_type.append('IMAGE')
                self.set_snapshots_render_image_data(uds_didv)
                self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
            elif uds_didv.name.split('_')[0] == 'uds2D':
                snapshot_info.ch_type.append('PLOT')
                self.set_snapshots_render_plot_data(uds_didv)
                self.generate_singlelayer_snapshots_Plot1U2Widget(snapshot_info)
            else:
                print('Snapmanager: Unknow uds data type')
            
        if 'Current (A)' in data3ds.channel_dict['Current']:
            uds_current = data3ds.get_Current()
            channel = uds_current.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('Current Map')
            
            if uds_current.name.split('_')[0] == 'uds3D':
                snapshot_info.ch_type.append('IMAGE')
                self.set_snapshots_render_image_data(uds_current)
                self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
            elif uds_current.name.split('_')[0] == 'uds2D':
                snapshot_info.ch_type.append('PLOT')
                self.set_snapshots_render_plot_data(uds_current)
                self.generate_singlelayer_snapshots_Plot1U2Widget(snapshot_info)
            else:
                print('Snapmanager: Unknow uds data type')
            
        if 'LI Demod 1 Y (A)' in data3ds.channel_dict['Phase']:
            uds_didv_phase = data3ds.get_Phase()
            channel = uds_didv_phase.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('dI/dV Phase Map')
            
            if uds_didv_phase.name.split('_')[0] == 'uds3D':
                snapshot_info.ch_type.append('IMAGE')
                self.set_snapshots_render_image_data(uds_didv_phase)
                self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
            elif uds_didv_phase.name.split('_')[0] == 'uds2D':
                snapshot_info.ch_type.append('PLOT')
                self.set_snapshots_render_plot_data(uds_didv_phase)
                self.generate_singlelayer_snapshots_Plot1U2Widget(snapshot_info)
            else:
                print('Snapmanager: Unknow uds data type')
        
        # pivotal_info
        if 'current>current (a)' in data3ds.header.keys():
            current = NumberExpression.float_to_simplified_number(data3ds.header['current>current (a)'])
            snapshot_info.pivotal_info.append('Current Setpoint(A):' + current)
        if 'bias>bias (v)' in data3ds.header.keys():
            bias = NumberExpression.float_to_simplified_number(data3ds.header['bias>bias (v)'])
            snapshot_info.pivotal_info.append('Bias Setpoint(V):' + bias)

        #snapshot_info.full_info = []
        snapshot_info.src_file_uuid = f"{uuid.uuid4()}.jason"
        self.snapshots_srcfile[srcfile_path] = snapshot_info.src_file_uuid + '@' + src_file_lastmodified
        self.save_metadata_srcfile()    
        self.save_snapshots(snapshot_info)
        
    def generate_snapshots_to_metafile_from_sxm(self, srcfile_path, src_file_lastmodified):
        srcfile_name = srcfile_path.split('/')[-1].split('.')[0]
        dataSxm = NanonisDataProcess.DataSxmStru(srcfile_path, srcfile_name)
        
        snapshot_info = SnapshotInfo(srcfile_path, src_file_lastmodified)
        
        if 'Z' in dataSxm.channel_dict['Topo']:
            uds3D_topo = dataSxm.get_Topo_fwd()
            channel = uds3D_topo.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('Topo')
            snapshot_info.ch_type.append('IMAGE')           

            #background subtract
            uds3D_topo_bg = ImgProc.ipBackgroundSubtract2D(uds3D_topo, 2, 'PerLine')
                        
            self.set_snapshots_render_image_data(uds3D_topo_bg)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
            
        if 'LI_Demod_1_X' in dataSxm.channel_dict['dIdV']:            
            uds3D_didv = dataSxm.get_dIdV_fwd()
            channel = uds3D_didv.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('dI/dV Map')
            snapshot_info.ch_type.append('IMAGE')
            
            self.set_snapshots_render_image_data(uds3D_didv)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
            
        if 'Current' in dataSxm.channel_dict['Current']:
            uds3D_current = dataSxm.get_Current_fwd()
            channel = uds3D_current.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('Current Map')
            snapshot_info.ch_type.append('IMAGE')
            
            self.set_snapshots_render_image_data(uds3D_current)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
            
        if 'LI_Demod_1_Y' in dataSxm.channel_dict['Phase']:
            uds3D_didv_phase = dataSxm.get_theta_fwd()
            channel = uds3D_didv_phase.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('dI/dV Phase Map') 
            snapshot_info.ch_type.append('IMAGE')
             
            self.set_snapshots_render_image_data(uds3D_didv_phase)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
        
        # pivotal_info
        if 'Current>Current (A)' in dataSxm.header.keys():
            current = NumberExpression.float_to_simplified_number(dataSxm.header['Current>Current (A)'])
            snapshot_info.pivotal_info.append('Current Setpoint(A):' + current)
        elif 'Z-CONTROLLER' in dataSxm.header.keys():
            current = dataSxm.header['Z-CONTROLLER']['Setpoint']
            snapshot_info.pivotal_info.append('Current Setpoint(A):' + current)
        else:
            pass
        if 'BIAS' in dataSxm.header.keys():
            bias = NumberExpression.float_to_simplified_number(dataSxm.header['BIAS'])
            snapshot_info.pivotal_info.append('Bias Setpoint(V):' + bias)
        
        #snapshot_info.full_info = []
        snapshot_info.src_file_uuid = f"{uuid.uuid4()}.jason"
        self.snapshots_srcfile[srcfile_path] = snapshot_info.src_file_uuid + '@' + src_file_lastmodified
        self.save_metadata_srcfile()    
        self.save_snapshots(snapshot_info)
        
    def generate_snapshots_to_metafile_from_dat(self, srcfile_path, src_file_lastmodified):
        srcfile_name = srcfile_path.split('/')[-1].split('.')[0]
        dataDat = NanonisDataProcess.DataDatStru(srcfile_path, srcfile_name)  
        
        snapshot_info = SnapshotInfo(srcfile_path, src_file_lastmodified)
        if dataDat.header['Experiment'] == 'bias spectroscopy':            
            if ('LI Demod 1 X (A)' in dataDat.channel_dict['dIdV']) or ('Input 2 (V)' in dataDat.channel_dict['dIdV']): 
                uds_didv = dataDat.get_dIdV()
                channel = uds_didv.info.get('Channel', None)
                if not channel == None:
                    snapshot_info.channel.append(channel)
                else:
                    snapshot_info.channel.append('dI/dV Map')
                    
                snapshot_info.ch_type.append('PLOT')
                self.set_snapshots_render_plot_data(uds_didv)
                self.generate_singlelayer_snapshots_Plot1U2Widget(snapshot_info)
                
            if 'Current (A)' in dataDat.channel_dict['Current']:
                uds_current = dataDat.get_Current()
                channel = uds_current.info.get('Channel', None)
                if not channel == None:
                    snapshot_info.channel.append(channel)
                else:
                    snapshot_info.channel.append('Current Map')
                
                snapshot_info.ch_type.append('PLOT')
                self.set_snapshots_render_plot_data(uds_current)
                self.generate_singlelayer_snapshots_Plot1U2Widget(snapshot_info)
                
            if 'LI Demod 1 Y (A)' in dataDat.channel_dict['Phase']:
                uds_didv_phase = dataDat.get_theta()
                channel = uds_didv_phase.info.get('Channel', None)
                if not channel == None:
                    snapshot_info.channel.append(channel)
                else:
                    snapshot_info.channel.append('dI/dV Phase Map')
                
                snapshot_info.ch_type.append('PLOT')
                self.set_snapshots_render_plot_data(uds_didv_phase)
                self.generate_singlelayer_snapshots_Plot1U2Widget(snapshot_info)
        elif dataDat.header['Experiment'] == 'Z spectroscopy':
            if 'Current (A)' in dataDat.channel_dict['I-Z']:
                uds_I_Z = dataDat.get_I_Z()
                channel = uds_I_Z.info.get('Channel', None)
                if not channel == None:
                    snapshot_info.channel.append(channel)
                else:
                    snapshot_info.channel.append('I-Z Map')
                
                snapshot_info.ch_type.append('PLOT')
                self.set_snapshots_render_plot_data(uds_I_Z)
                self.generate_singlelayer_snapshots_Plot1U2Widget(snapshot_info)
                
        # pivotal_info
        if 'Current>Current (A)' in dataDat.header.keys():
            current = NumberExpression.float_to_simplified_number(float(dataDat.header['Current>Current (A)']))
            snapshot_info.pivotal_info.append('Current Setpoint(A):' + current)
        if 'Bias>Bias (V)' in dataDat.header.keys():
            bias = NumberExpression.float_to_simplified_number(float(dataDat.header['Bias>Bias (V)']))
            snapshot_info.pivotal_info.append('Bias Setpoint(V):' + bias)

        #snapshot_info.full_info = []
        snapshot_info.src_file_uuid = f"{uuid.uuid4()}.jason"
        self.snapshots_srcfile[srcfile_path] = snapshot_info.src_file_uuid + '@' + src_file_lastmodified
        self.save_metadata_srcfile()    
        self.save_snapshots(snapshot_info)
        
    def generate_snapshots_to_metafile_from_TFR(self, srcfile_path, src_file_lastmodified):
        dataTFR = LFDataProcess.Data1FLStru(srcfile_path)
        snapshot_info = SnapshotInfo(srcfile_path, src_file_lastmodified)
        
        uds_topo = dataTFR.get_Topo()
        channel = uds_topo.info.get('Channel', None)
        if not channel == None:
            snapshot_info.channel.append(channel)
        else:
            snapshot_info.channel.append('Topo')
        snapshot_info.ch_type.append('IMAGE')
        #background subtract
        uds_topo_bg = ImgProc.ipBackgroundSubtract2D(uds_topo, 2, 'PerLine')
        
        self.set_snapshots_render_image_data(uds_topo_bg)
        self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
        
        # pivotal_info
        
        current = str(dataTFR.header['Current Setpoint (A)'])
        snapshot_info.pivotal_info.append('Current Setpoint(A):' + current)
        bias = str(dataTFR.header['Bias (V)'])
        snapshot_info.pivotal_info.append('Bias (V):' + bias)
        
        #snapshot_info.full_info = []
        snapshot_info.src_file_uuid = f"{uuid.uuid4()}.jason"
        self.snapshots_srcfile[srcfile_path] = snapshot_info.src_file_uuid + '@' + src_file_lastmodified
        self.save_metadata_srcfile()    
        self.save_snapshots(snapshot_info)      
        
    def generate_snapshots_to_metafile_from_1FL(self, srcfile_path, src_file_lastmodified):
        data1fl = LFDataProcess.Data1FLStru(srcfile_path)
        snapshot_info = SnapshotInfo(srcfile_path, src_file_lastmodified)
        
        uds_didv = data1fl.get_dIdV()
        channel = uds_didv.info.get('Channel', None)
        if not channel == None:
            snapshot_info.channel.append(channel)
        else:
            snapshot_info.channel.append('Topo')
        snapshot_info.ch_type.append('IMAGE')
        
        self.set_snapshots_render_image_data(uds_didv)
        self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
        
        # pivotal_info
        
        current = str(data1fl.header['Current Setpoint (A)'])
        snapshot_info.pivotal_info.append('Current Setpoint(A):' + current)
        bias = str(data1fl.header['Bias (V)'])
        snapshot_info.pivotal_info.append('Bias (V):' + bias)
        
        #snapshot_info.full_info = []
        snapshot_info.src_file_uuid = f"{uuid.uuid4()}.jason"
        self.snapshots_srcfile[srcfile_path] = snapshot_info.src_file_uuid + '@' + src_file_lastmodified
        self.save_metadata_srcfile()    
        self.save_snapshots(snapshot_info)    
        
    def generate_snapshots_to_metafile_from_uds(self, srcfile_path, src_file_lastmodified):
        dataUdp = UdsDataProcess(srcfile_path)
        
        snapshot_info = SnapshotInfo(srcfile_path, src_file_lastmodified)
        
        # only one channel
        uds_data = dataUdp.readFromFile()
        channel = uds_data.info.get('Channel', None)
        if not channel == None:
            snapshot_info.channel.append(channel)
        else:
            snapshot_info.channel.append('Channel: ?')
            
        snapshot_info.ch_type.append('IMAGE')
        
        self.set_snapshots_render_image_data(uds_data)
        self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
        
        #snapshot_info.full_info = []
        snapshot_info.src_file_uuid = f"{uuid.uuid4()}.jason"
        self.snapshots_srcfile[srcfile_path] = snapshot_info.src_file_uuid + '@' + src_file_lastmodified
        self.save_metadata_srcfile()    
        self.save_snapshots(snapshot_info)
        
    """ Load and send data to var list for gui manager """
    def load_channel_data(self, srcfile_path, channel):
        srcfile_name = srcfile_path.split('/')[-1].split('.')[0]
        # file suffix/format
        suffix = srcfile_path.split('.')[-1]      
                
        if suffix == '3ds':
            data3ds = NanonisDataProcess.Data3dsStru(srcfile_path, srcfile_name)
            if channel == 'Topo':
                return data3ds.get_Topo()
            elif channel == 'dI/dV Map':
                return data3ds.get_dIdV_data()
            elif channel == 'Current Map':
                return data3ds.get_Current()
            elif channel == 'dI/dV Phase Map':
                return data3ds.get_Phase()
            else:
                print('Load 3ds channel data error: Unknown channel!')
                return None
        elif suffix == 'sxm':
            dataSxm = NanonisDataProcess.DataSxmStru(srcfile_path, srcfile_name)
            if channel == 'Topo':
                return dataSxm.get_Topo_fwd()
            elif channel == 'dI/dV Map':
                return dataSxm.get_dIdV_fwd()
            elif channel == 'Current Map':
                return dataSxm.get_Current_fwd()
            elif channel =='dI/dV Phase Map':
                return dataSxm.get_theta()
            else:
                print('Load sxm channel data error: Unknown channel!')
                return None
        elif suffix == 'dat':
            dataDat = NanonisDataProcess.DataDatStru(srcfile_path, srcfile_name)
            if channel == 'dI/dV Curve':
                return dataDat.get_dIdV()
            elif channel == 'Current Curve':
                return dataDat.get_Current()
            elif channel =='dI/dV Phase Curve':
                return dataDat.get_theta()
            elif channel == 'I(Z) Curve':
                return dataDat.get_I_Z()
            else:
                print('Load sxm channel data error: Unknown channel!')
                return None
        elif suffix == 'TFR':
            dataTFR = LFDataProcess.Data1FLStru(srcfile_path)
            return dataTFR.get_Topo()
        elif suffix == '1FL':
            data1FL = LFDataProcess.Data1FLStru(srcfile_path)
            return data1FL.get_dIdV()
        elif suffix == 'uds':
            if channel == None:
                pass
        else:
            return None
            print('Load channel data error: Unsupported file suffix!') 