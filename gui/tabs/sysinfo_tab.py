from nicegui import ui
import platform
import psutil
import sys


def get_system_stats():
    return {
        "cpu_percent": psutil.cpu_percent(),
        "mem_percent": psutil.virtual_memory().percent,
        "process_mem_mb": psutil.Process().memory_info().rss / 1024 / 1024,
        "os": platform.system(),
        "python": sys.version.split()[0],
        "cpu_count": psutil.cpu_count(),
        "total_mem_mb": psutil.virtual_memory().total / 1024 / 1024,
        "used_mem_mb": psutil.virtual_memory().used / 1024 / 1024,
        "process_cpu": psutil.Process().cpu_percent(),
    }


def get_sysinfo():
    stats = get_system_stats()
    return (
        f"# 系统信息\n"
        f"**CPU使用率:** {stats['cpu_percent']:.1f}%  \n"
        f"**内存使用:** {stats['mem_percent']:.1f}%  \n"
        f"**进程内存:** {stats['process_mem_mb']:.1f} MB  \n"
        f"**操作系统:** {stats['os']}  \n"
        f"**Python版本:** {stats['python']}  \n"
        f"**CPU核心数:** {stats['cpu_count']}  \n"
        f"**总内存:** {stats['total_mem_mb']:.1f} MB  \n"
        f"**已用内存:** {stats['used_mem_mb']:.1f} MB  \n"
        f"**进程CPU使用:** {stats['process_cpu']:.1f}%"
    )


def render_sysinfo_tab():
    sysinfo_label = ui.markdown(get_sysinfo())

    def update():
        sysinfo_label.content = get_sysinfo()

    ui.timer(2, update)
