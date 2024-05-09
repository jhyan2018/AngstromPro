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
from PyQt5 import QtGui
"""
User Modules
"""
class SnapshotManager:
    def __init__(self, snapshots_dir):
        self.snapshots_dir = snapshots_dir
        self.snapshots_png_name = {}
        self.snapshots_last_modified = {}
        self.snapshots_channel = {}
        
        self.metadata_png_name = os.path.join(snapshots_dir, "metadata_pngname.json")
        self.metadata_last_modified = os.path.join(snapshots_dir, "metadata_lastmodified.json")
        self.metadata_channel = os.path.join(snapshots_dir, "metadata_channel.json")

        if not os.path.exists(snapshots_dir):
            os.makedirs(snapshots_dir)

        self.load_metadata()

    def load_metadata(self):
        if os.path.exists(self.metadata_png_name):
            with open(self.metadata_png_name, "r") as f:
                self.snapshots_png_name = json.load(f)
        else:
            self.snapshots_png_name = {}
          
        if os.path.exists(self.metadata_last_modified):
            with open(self.metadata_last_modified, "r") as f:
                self.snapshots_last_modified = json.load(f)
        else:
            self.snapshots_last_modified = {}
            
        if os.path.exists(self.metadata_channel):
            with open(self.metadata_channel, "r") as f:
                self.snapshots_channel = json.load(f)
        else:
            self.snapshots_channel = {}

    def save_metadata(self):
        with open(self.metadata_png_name, "w") as f:
            json.dump(self.snapshots_png_name, f, indent=4)
   
        with open(self.metadata_last_modified, "w") as f:
            json.dump(self.snapshots_last_modified, f, indent=4)  
            
        with open(self.metadata_channel, "w") as f:
            json.dump(self.snapshots_channel, f, indent=4)
    
    def save_snapshots(self, srcfile_path, srcfile_lastmodified, pixmap_list, channel_list, channel_layer_list):
        png_name_list = []
        pixmap_counts = 0
        
        for index, channel in enumerate(channel_list):
            uuid_name = f"{uuid.uuid4()}"
            if channel_layer_list[index] == 1:
                png_name = uuid_name + '.png'
                snapshot_path = os.path.join(self.snapshots_dir, f"{png_name}")
                pixmap_list[pixmap_counts].save(snapshot_path)
                pixmap_counts += 1
            elif channel_layer_list[index] >= 2:
                png_name = uuid_name
                png_subpath = os.path.join(self.snapshots_dir, f"{png_name}")
                os.makedirs(png_subpath)
                for i in range(channel_layer_list[index]):
                    snapshot_path = os.path.join(png_subpath, f"l{i}.png")
                    print(snapshot_path)
                    pixmap_list[pixmap_counts].save(snapshot_path)
                    pixmap_counts += 1
            else:
                print('Snapshots: Unsupported channel layers!')            
            png_name_list.append(png_name)        
            
        pixmap_list.clear()           
        
        separator = '>'
        self.snapshots_png_name[srcfile_path] = separator.join(png_name_list)
        self.snapshots_last_modified[srcfile_path] = srcfile_lastmodified
        self.snapshots_channel[srcfile_path] = separator.join(channel_list)
        self.save_metadata()
           
    def get_snapshots_info(self, srcfile_path):
        pngs_name = self.snapshots_png_name.get(srcfile_path, None)
        last_modified = self.snapshots_last_modified.get(srcfile_path, None)
        channels = self.snapshots_channel.get(srcfile_path, None)
        
        if pngs_name and last_modified:
            png_name_list = pngs_name.split('>')
            png_path_list = []
            for png_name in png_name_list:
                png_path = os.path.join(self.snapshots_dir, f"{png_name}")
                png_path_list.append(png_path)
            
            channel_list = channels.split('>')
                
            return png_path_list, last_modified, channel_list
        else:
            return None, None, None
        
    def generate_snapshots(self, srcfile_path):
        pixmap_list = []
        channel_list = []
        channel_layer_list = []
        
        pixmap = QtGui.QPixmap(srcfile_path)
        
        pixmap_list.append(pixmap)
        pixmap_list.append(pixmap)
        
        channel_list.append('topo')
        channel_layer_list.append(2)
        
        pixmap_list.append(pixmap)
        pixmap_list.append(pixmap)
        pixmap_list.append(pixmap)
        pixmap_list.append(pixmap)
        
        channel_list.append('didv')
        channel_layer_list.append(4)
        
        return pixmap_list, channel_list, channel_layer_list