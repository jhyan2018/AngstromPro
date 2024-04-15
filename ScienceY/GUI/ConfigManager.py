# -*- coding: utf-8 -*-
"""
Created on Sun Apr 14 23:36:43 2024

@author: jiahaoYan
"""


class ConfigManager:
    @staticmethod
    def save_settings_to_file(filename, settings):
        """Save settings to a file, organized by sections."""
        with open(filename, 'w') as file:
            for section, pairs in settings.items():
                file.write(f"[{section}]\n")
                for key, value in pairs.items():
                    file.write(f"{key}={value}\n")
                file.write("\n")

    @staticmethod
    def load_settings_from_file(filename):
        """Load settings from a file, organized by sections."""
        settings = {}
        current_section = None

        with open(filename, 'r') as file:
            for line in file:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                    settings[current_section] = {}
                elif '=' in line and current_section:
                    key, value = line.split('=', 1)
                    settings[current_section][key.strip()] = value.strip()

        return settings
