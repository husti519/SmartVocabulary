import sys
import os

def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for packaged executable.
    Used for static assets (icons, css, images) that are bundled inside the EXE.
    """
    try:
        # PyInstaller/Nuitka/fbs store bundled resources in a temp folder
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_external_path(filename):
    """
    Get path for files that should live NEXT to the executable file.
    Used for config files (.json) and user-editable prompts (.txt).
    """
    if hasattr(sys, 'frozen') or hasattr(sys, 'real_prefix'):
        # Path where the actual .exe file is located
        base_path = os.path.dirname(sys.executable)
    else:
        # Development environment (running via python main.py)
        base_path = os.path.abspath(".")

    return os.path.join(base_path, filename)
