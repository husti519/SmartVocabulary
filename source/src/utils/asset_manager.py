from PySide6.QtGui import QIcon
import os
import logging
from .path_utils import get_resource_path

class AssetManager:
    _icons = {}

    @classmethod
    def get_icon(cls, filename):
        """Returns a cached QIcon instance for the given filename in src/assets."""
        if filename not in cls._icons:
            # Use get_resource_path for bundled assets
            path = get_resource_path(os.path.join("assets", filename))
            
            # Check if file actually exists
            if not os.path.exists(path):
                logging.warning(f"AssetManager: Icon file not found at {path}")
                cls._icons[filename] = QIcon() 
            else:
                cls._icons[filename] = QIcon(path)
                
        return cls._icons[filename]
