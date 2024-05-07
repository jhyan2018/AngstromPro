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

"""
User Modules
"""
class SnapshotManager:
    def __init__(self, snapshots_dir):
        self.snapshots_dir = snapshots_dir
        self.snapshots_png_name = {}
        self.snapshots_last_modified = {}
        
        self.metadata_png_name = os.path.join(snapshots_dir, "metadata_pngname.json")
        self.metadata_last_modified = os.path.join(snapshots_dir, "metadata_lastmodified.json")

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

    def save_metadata(self):
        with open(self.metadata_png_name, "w") as f:
            json.dump(self.snapshots_png_name, f)
   
        with open(self.metadata_last_modified, "w") as f:
            json.dump(self.snapshots_last_modified, f)        
    
    def save_snapshot(self, srcfile_path, srcfile_lastmodified, pixmap, old_pngname=None):
            png_name = f"{uuid.uuid4()}.png"
            snapshot_path = os.path.join(self.snapshots_dir, f"{png_name}")
            pixmap.save(snapshot_path)

            self.snapshots_png_name[srcfile_path] = png_name
            self.snapshots_last_modified[srcfile_path] = srcfile_lastmodified
            self.save_metadata()
            
            #remove old snapshot png
            if not old_pngname:
                old_snapshot_path = os.path.join(self.snapshots_dir, f"{old_pngname}") 
                if os.path.exists(old_snapshot_path):
                    os.remove(old_snapshot_path)    
                
    def get_snapshot(self, srcfile_path):
        png_name = self.snapshots_png_name.get(srcfile_path, None)
        last_modified = self.snapshots_last_modified.get(srcfile_path, None)
        
        if png_name and last_modified:
            png_path = os.path.join(self.snapshots_dir, f"{png_name}")
            return png_path, last_modified
        else:
            return None, None   