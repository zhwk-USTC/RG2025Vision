# GUI模块初始化
# 标识UI是否正在运行的全局变量
_is_ui_running = False

def set_ui_running(state=True):
    """设置UI运行状态"""
    global _is_ui_running
    _is_ui_running = state
    return _is_ui_running

def is_ui_running():
    """获取UI运行状态"""
    global _is_ui_running
    return _is_ui_running
