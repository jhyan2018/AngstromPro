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
        pass
    
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
                for i in range(int(snapshot_info.ch_layers[index])):
                    snapshot_path = os.path.join(png_subpath, f"l{i}.png")
                    #print(snapshot_path)
                    snapshot_info.pixmap[pixmap_counts].save(snapshot_path)
                    pixmap_counts += 1
            else:
                print('Snapshots: Unsupported channel layers!')       

        self.save_metadata_file(snapshot_info)
        
    def generate_snapshots(self, srcfile_path, src_file_lastmodified):
        # file suffix/format
        suffix = srcfile_path.split('.')[-1]      
                
        if suffix == '3ds':
            self.generate_snapshots_3ds(srcfile_path, src_file_lastmodified)
        elif suffix == 'sxm':
            self.generate_snapshots_sxm(srcfile_path, src_file_lastmodified)
        elif suffix == 'TFR':
            self.generate_snapshots_TFR(srcfile_path, src_file_lastmodified)
        elif suffix == '1FL':
            self.generate_snapshots_1FL(srcfile_path, src_file_lastmodified)
        elif suffix == 'uds':
            self.generate_snapshots_uds(srcfile_path, src_file_lastmodified)
        else:
            print('Generate snapshots error: Unsupported file suffix!')
    def generate_snapshots_Img2U3Widget(self, uds_data, snapshot_info):
        self.snapshots_render_image.setUdsData(uds_data)
        
        layer_value = self.snapshots_render_image.uds_var_layer_value
        separator = ','
        snapshot_info.ch_layer_value.append(separator.join(layer_value))
        layers = len(layer_value)
        snapshot_info.ch_layers.append(str(layers))
        
        layer_scale = []
        self.snapshots_render_image.imageLayerChangedSlotDisconnect()            
        for layer in range(layers):
            self.snapshots_render_image.ui_sb_image_layers.setValue(layer)
            self.snapshots_render_image.imageLayerChanged()                         
            
            pixmap = QtGui.QPixmap(self.snapshots_render_image.static_canvas.size())
            self.snapshots_render_image.static_canvas.render(pixmap)
            snapshot_info.pixmap.append(pixmap)
            
            scale_u_v = self.snapshots_render_image.ui_scale_widget.data_upper_value
            scale_l_v = self.snapshots_render_image.ui_scale_widget.data_lower_value 
            layer_scale.append(NumberExpression.float_to_simplified_number(scale_l_v))
            layer_scale.append(NumberExpression.float_to_simplified_number(scale_u_v))
            
        snapshot_info.ch_layer_scale.append(separator.join(layer_scale))     
        self.snapshots_render_image.imageLayerChangedSlotConnect()
        
    def generate_snapshots_3ds(self, srcfile_path, src_file_lastmodified):
        srcfile_name = srcfile_path.split('/')[-1].split('.')[0]
        data3ds = NanonisDataProcess.Data3dsStru(srcfile_path, srcfile_name)  
        
        snapshot_info = SnapshotInfo(srcfile_path, src_file_lastmodified)
        #snapshot_info.pivotal_info = []
        #snapshot_info.full_info = []
        snapshot_info.src_file_uuid = f"{uuid.uuid4()}.jason"
        self.snapshots_srcfile[srcfile_path] = snapshot_info.src_file_uuid + '@' + src_file_lastmodified
        self.save_metadata_srcfile()
        
        if 'Z (m)' in data3ds.channel_list:
            snapshot_info.channel.append('Z (m)')
            snapshot_info.ch_type.append('IMAGE')
            
            uds3D_topo = data3ds.get_Topo()
            #background subtract
            uds3D_topo_bg = ImgProc.ipBackgroundSubtract2D(uds3D_topo, 2, 'PerLine')          
            self.generate_snapshots_Img2U3Widget(uds3D_topo_bg, snapshot_info)
                    
        if ('LI Demod 1 X (A)' in data3ds.channel_list) or ('Input 2 (V)' in data3ds.channel_list): 
            snapshot_info.channel.append('LI Demod 1 X (A)')
            snapshot_info.ch_type.append('IMAGE')
            
            uds3D_didv = data3ds.get_dIdV_data()
            self.generate_snapshots_Img2U3Widget(uds3D_didv, snapshot_info)
            
        if 'Current (A)' in data3ds.channel_list:
            snapshot_info.channel.append('Current (A)')
            snapshot_info.ch_type.append('IMAGE')
            
            uds3D_current = data3ds.get_Current()
            self.generate_snapshots_Img2U3Widget(uds3D_current, snapshot_info)
            
        if 'LI Demod 1 Y (A)' in data3ds.channel_list:
            snapshot_info.channel.append('LI Demod 1 Y (A)')
            snapshot_info.ch_type.append('IMAGE')
            
            uds3D_didv_phase = data3ds.get_Phase()
            self.generate_snapshots_Img2U3Widget(uds3D_didv_phase, snapshot_info)
            
        self.save_snapshots(snapshot_info)
        
    def generate_snapshots_sxm(self, srcfile_path, src_file_lastmodified):
        pass
    """
            globals()['dataSxm'] = NanonisDataProcess.DataSxmStru(full_path, file_name)
            if 'Z' in dataSxm.channel_list[0]:
                globals()['uds3D_'+file_name+'_topo_fwd'] = dataSxm.get_Topo_fwd()
                if dataSxm.channel_list[1][dataSxm.channel_list[0].index('Z')] == 'both':
                    globals()['uds3D_'+file_name+'_topo_bwd'] = dataSxm.get_Topo_bwd()
            if 'LI_Demod_1_X' in dataSxm.channel_list[0]:
                globals()['uds3D_'+file_name+'_dIdV_fwd'] = dataSxm.get_dIdV_fwd()
                if dataSxm.channel_list[1][dataSxm.channel_list[0].index('LI_Demod_1_X')] == 'both':
                    globals()['uds3D_'+file_name+'_dIdV_bwd'] = dataSxm.get_dIdV_bwd()
            if 'Current' in dataSxm.channel_list[0]:
                globals()['uds3D_'+file_name+'_Currrent_fwd'] = dataSxm.get_Current_fwd()
                if dataSxm.channel_list[1][dataSxm.channel_list[0].index('Current')] == 'both':
                    globals()['uds3D_'+file_name+'_Current_bwd'] = dataSxm.get_Current_bwd()
            if 'LI_Demod_1_Y' in dataSxm.channel_list[0]:
                globals()['uds3D_'+file_name+'_theta'] = dataSxm.get_theta()
    """
    def generate_snapshots_TFR(self, srcfile_path, src_file_lastmodified):
        pass
        """    
        data1fl = LFDataProcess.Data1FLStru(full_path)
        globals()['uds3D_'+file_name+'_topo'] = data1fl.get_data() 
        """ 
    def generate_snapshots_1FL(self, srcfile_path, src_file_lastmodified):
        pass
        """    
        data1fl = LFDataProcess.Data1FLStru(full_path)
            globals()['uds3D_'+file_name+'_dIdV'] = data1fl.get_data()
        """     
    def generate_snapshots_uds(self, srcfile_path, src_file_lastmodified):
        pass
        """
        udp = UdsDataProcess(full_path)
            uds_data = udp.readFromFile()
            globals()[uds_data.name] = uds_data
        """