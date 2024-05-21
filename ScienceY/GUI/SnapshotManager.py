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

"""
Third-party Modules
"""
from PyQt5 import QtGui, QtWidgets
"""
User Modules
"""
from ..GUI.Image2Uds3Widget import Image2Uds3Widget
from ..RawDataProcess import NanonisDataProcess
from ..RawDataProcess.UdsDataProcess import UdsDataProcess
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

        if 'Z (m)' in data3ds.channel_list:
            uds3D_topo = data3ds.get_Topo()
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
                    
        if ('LI Demod 1 X (A)' in data3ds.channel_list) or ('Input 2 (V)' in data3ds.channel_list): 
            uds3D_didv = data3ds.get_dIdV_data()
            channel = uds3D_didv.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('dI/dV Map')
            snapshot_info.ch_type.append('IMAGE')
            
            self.set_snapshots_render_image_data(uds3D_didv)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
            
        if 'Current (A)' in data3ds.channel_list:
            uds3D_current = data3ds.get_Current()
            channel = uds3D_current.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('Current Map')
            snapshot_info.ch_type.append('IMAGE')
            
            self.set_snapshots_render_image_data(uds3D_current)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
            
        if 'LI Demod 1 Y (A)' in data3ds.channel_list:
            uds3D_didv_phase = data3ds.get_Phase()
            channel = uds3D_didv_phase.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('dI/dV Phase Map')
            snapshot_info.ch_type.append('IMAGE')
            
            self.set_snapshots_render_image_data(uds3D_didv_phase)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
        
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
        
        if 'Z' in dataSxm.channel_list[0]:
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
            
        if 'LI_Demod_1_X' in dataSxm.channel_list[0]:            
            uds3D_didv = dataSxm.get_dIdV_fwd()
            channel = uds3D_didv.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('dI/dV Map')
            snapshot_info.ch_type.append('IMAGE')
            
            self.set_snapshots_render_image_data(uds3D_didv)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
            
        if 'Current' in dataSxm.channel_list[0]:
            uds3D_current = dataSxm.get_Current_fwd()
            channel = uds3D_current.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('Current Map')
            snapshot_info.ch_type.append('IMAGE')
            
            self.set_snapshots_render_image_data(uds3D_current)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
            
        if 'LI_Demod_1_Y' in dataSxm.channel_list[0]:
            uds3D_didv_phase = dataSxm.get_theta()
            channel = uds3D_didv_phase.info.get('Channel', None)
            if not channel == None:
                snapshot_info.channel.append(channel)
            else:
                snapshot_info.channel.append('dI/dV Phase Map') 
            snapshot_info.ch_type.append('IMAGE')
             
            self.set_snapshots_render_image_data(uds3D_didv_phase)
            self.generate_singlelayer_snapshots_Img2U3Widget(snapshot_info)
        
        # pivotal_info
        if 'current>current (a)' in dataSxm.header.keys():
            current = NumberExpression.float_to_simplified_number(dataSxm.header['current>current (a)'])
            snapshot_info.pivotal_info.append('Current Setpoint(A):' + current)
        if 'bias>bias (v)' in dataSxm.header.keys():
            bias = NumberExpression.float_to_simplified_number(dataSxm.header['bias>bias (v)'])
            snapshot_info.pivotal_info.append('Bias Setpoint(V):' + bias)
        
        #snapshot_info.full_info = []
        snapshot_info.src_file_uuid = f"{uuid.uuid4()}.jason"
        self.snapshots_srcfile[srcfile_path] = snapshot_info.src_file_uuid + '@' + src_file_lastmodified
        self.save_metadata_srcfile()    
        self.save_snapshots(snapshot_info)

    def generate_snapshots_to_metafile_from_TFR(self, srcfile_path, src_file_lastmodified):
        pass
        """    
        data1fl = LFDataProcess.Data1FLStru(full_path)
        globals()['uds3D_'+file_name+'_topo'] = data1fl.get_data() 
        """ 
    def generate_snapshots_to_metatfile_from_1FL(self, srcfile_path, src_file_lastmodified):
        pass
        """    
        data1fl = LFDataProcess.Data1FLStru(full_path)
            globals()['uds3D_'+file_name+'_dIdV'] = data1fl.get_data()
        """     
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
                print('Load channel data error: Unknown channel!')
                return None
        elif suffix == 'sxm':
            if channel == None:
                pass
        elif suffix == 'TFR':
            pass
        elif suffix == '1FL':
            pass
        elif suffix == 'uds':
            if channel == None:
                pass
        else:
            return None
            print('Load channel data error: Unsupported file suffix!') 