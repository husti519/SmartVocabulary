import sys
import os


def _get_source_root():
    """Return the project root while running from source."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
            base_path = _get_source_root()
    except Exception:
        base_path = _get_source_root()

    return os.path.join(base_path, relative_path)

def get_external_path(filename):
    """
    Get path for files that should live NEXT to the executable file.
    Used for config files (.json) and user-editable prompts (.txt).
    """
    if getattr(sys, "frozen", False):
        # Path where the actual .exe file is located
        base_path = os.path.dirname(sys.executable)
    else:
        # Development environment (running via python main.py)
        base_path = _get_source_root()

    return os.path.join(base_path, filename)
