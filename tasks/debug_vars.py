import threading
from typing import Any, Dict, Optional
import base64

debug_vars: Dict[str, Any] = {}
debug_images: Dict[str, Any] = {}
debug_vars_lock = threading.Lock()

def reset_debug_vars():
    with debug_vars_lock:
        debug_vars.clear()

def set_debug_var(key, value):
    with debug_vars_lock:
        debug_vars[key] = value
        
def set_debug_image(key, value):
    with debug_vars_lock:
        debug_images[key] = value        

def get_debug_vars():
    with debug_vars_lock:
        return dict(debug_vars)
    
def get_debug_images():
    with debug_vars_lock:
        return dict(debug_images)