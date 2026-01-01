import  sys, os

def get_resource_path(relative_path):
    """
    Get the absolute path of the resources, compatible with PyInstaller
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)