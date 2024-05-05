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
        self.metadata_file_name = os.path.join(snapshots_dir, "metadata_filename.json")
        self.metadata_last_modified = os.path.join(snapshots_dir, "metadata_lastmodified.json")
        self.snapshots_file_name = {}
        self.snapshots_last_modified = {}

        if not os.path.exists(snapshots_dir):
            os.makedirs(snapshots_dir)

        self.load_metadata()

    def load_metadata(self):
        if os.path.exists(self.metadata_file_name):
            with open(self.metadata_file_name, "r") as f:
                self.snapshots_file_name = json.load(f)
        else:
            self.snapshots_file_name = {}
          
        if os.path.exists(self.metadata_last_modified):
            with open(self.metadata_last_modified, "r") as f:
                self.snapshots_last_modified = json.load(f)
        else:
            self.snapshots_last_modified = {}

    def save_metadata(self):
        with open(self.metadata_file_name, "w") as f:
            json.dump(self.snapshots_file_name, f)
   
        with open(self.metadata_last_modified, "w") as f:
            json.dump(self.snapshots_last_modified, f)        
    
    def save_snapshot(self, filename, lastmodified, pixmap, old_png_name=None):
            png_name = f"{uuid.uuid4()}.png"
            snapshot_path = os.path.join(self.snapshots_dir, f"{png_name}")
            pixmap.save(snapshot_path)  

            self.snapshots_file_name[filename] = png_name
            self.snapshots_last_modified[filename] = lastmodified
            self.save_metadata()
            
            #remove old snapshot png
            if not old_png_name:
                old_snapshot_path = os.path.join(self.snapshots_dir, f"{old_png_name}") 
                if os.path.exists(old_snapshot_path):
                    os.remove(old_snapshot_path)
                
    def get_snapshot(self, filename):
        png_name = self.snapshots_file_name.get(filename, None)
        last_modified = self.snapshots_last_modified.get(filename, None)
        if png_name and last_modified:
            png_path = os.path.join(self.snapshots_dir, f"{png_name}")
            return png_path, last_modified
        else:
            return None, None   

"""
    def save_snapshot(self):
        # Simulating taking a snapshot, using a QFileDialog to select an image
        filename, _ = QFileDialog.getOpenFileName(self, "Select Image to Save", "", "Images (*.png *.xpm *.jpg)")
        if filename:
            pixmap = QPixmap(filename)
            name = os.path.basename(filename).split(".")[0]
            self.snapshot_manager.save_snapshot(filename, pixmap)
            self.label.setText(f"Snapshot saved as {name}")

    def show_snapshot(self):
        name = "E:/gdrive/Python/examples/helium_states.png"  # Replace with logic to determine snapshot name
        snapshot_path = self.snapshot_manager.get_snapshot(name)

            pixmap = QPixmap(snapshot_path)
            self.label.setPixmap(pixmap)



    snapshots_dir = QDir.homePath() + "/snapshots"  # Save snapshots in the user's home directory
    SnapshotManager(snapshots_dir)
"""
