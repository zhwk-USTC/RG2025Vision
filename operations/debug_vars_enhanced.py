from collections import deque
import itertools
import threading
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class DebugLevel(Enum):
    """调试变量的级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

class DebugCategory(Enum):
    """调试变量的分类"""
    STATUS = "status"
    POSITION = "position"
    DETECTION = "detection"
    CONTROL = "control"
    TIMING = "timing"
    ERROR = "error"
    IMAGE = "image"

@dataclass
class DebugEntry:
    """调试变量条目"""
    key: str
    value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    level: DebugLevel = DebugLevel.INFO
    category: DebugCategory = DebugCategory.STATUS
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'key': self.key,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'category': self.category.value,
            'description': self.description
        }

@dataclass
class DebugImageEntry:
    """调试图像条目"""
    key: str
    image: Any
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""
    size: Optional[tuple] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'key': self.key,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'size': self.size
        }

class EnhancedDebugVars:
    """增强版调试变量管理器（历史使用 deque，最新在最上面）"""

    def __init__(self, max_entries: int = 1000):
        self._variables: Dict[str, DebugEntry] = {}
        self._images: Dict[str, DebugImageEntry] = {}

        # 用 deque 存历史，最新 appendleft；maxlen 自动裁剪
        self._history: deque[DebugEntry] = deque(maxlen=max_entries)

        # 可选：如果也想给图像历史按时间显示，可以打开下面两行
        # self._image_history: deque[DebugImageEntry] = deque(maxlen=max_entries)

        self._lock = threading.Lock()
        self._max_entries = max_entries

    def set_var(self, key: str, value: Any,
                level: DebugLevel = DebugLevel.INFO,
                category: DebugCategory = DebugCategory.STATUS,
                description: str = "") -> None:
        """设置调试变量（历史最新在最上）"""
        with self._lock:
            entry = DebugEntry(key, value, datetime.now(), level, category, description)
            self._variables[key] = entry
            # 最新放到最前面
            self._history.appendleft(entry)

    def set_image(self, key: str, image: Any, description: str = "") -> None:
        """设置调试图像"""
        with self._lock:
            size = None
            if hasattr(image, 'shape'):  # numpy array
                size = image.shape
            elif hasattr(image, 'size'):  # PIL Image
                size = image.size
            entry = DebugImageEntry(key, image, datetime.now(), description, size)
            self._images[key] = entry
            # 若需要图像历史，也可 appendleft
            # self._image_history.appendleft(entry)

    def get_vars_by_category(self, category: DebugCategory) -> Dict[str, DebugEntry]:
        with self._lock:
            return {k: v for k, v in self._variables.items() if v.category == category}

    def get_vars_by_level(self, level: DebugLevel) -> Dict[str, DebugEntry]:
        with self._lock:
            return {k: v for k, v in self._variables.items() if v.level == level}

    def get_all_vars(self) -> Dict[str, DebugEntry]:
        with self._lock:
            return dict(self._variables)

    def get_all_images(self) -> Dict[str, DebugImageEntry]:
        with self._lock:
            return dict(self._images)

    def get_history(self, limit: int = 100) -> List[DebugEntry]:
        """获取历史记录（最新在最前）。limit=None/0 返回全部。"""
        with self._lock:
            if not limit:
                # 转为 list，已是从最新到最旧
                return list(self._history)
            # 只取前 limit 个（最新的若干条）
            return list(itertools.islice(self._history, 0, limit))

    # 如果你也想获取图像历史，启用下面的方法
    # def get_image_history(self, limit: int = 100) -> List[DebugImageEntry]:
    #     with self._lock:
    #         if not limit:
    #             return list(self._image_history)
    #         return list(itertools.islice(self._image_history, 0, limit))

    def clear_category(self, category: DebugCategory) -> None:
        with self._lock:
            keys_to_remove = [k for k, v in self._variables.items() if v.category == category]
            for key in keys_to_remove:
                del self._variables[key]
            # 同时从历史里移除对应条目
            if keys_to_remove:
                self._history = deque(
                    (e for e in self._history if e.key not in keys_to_remove),
                    maxlen=self._max_entries
                )

    def clear_all(self) -> None:
        with self._lock:
            self._variables.clear()
            self._images.clear()
            self._history.clear()
            # 若启用图像历史： self._image_history.clear()

    def export_summary(self) -> Dict[str, Any]:
        """导出汇总信息（latest_entries 为最新在前的前10条）"""
        with self._lock:
            summary = {
                'total_vars': len(self._variables),
                'total_images': len(self._images),
                'by_category': {},
                'by_level': {},
                'latest_entries': [e.to_dict() for e in itertools.islice(self._history, 0, 10)]
            }
            for category in DebugCategory:
                count = sum(1 for v in self._variables.values() if v.category == category)
                if count > 0:
                    summary['by_category'][category.value] = count
            for level in DebugLevel:
                count = sum(1 for v in self._variables.values() if v.level == level)
                if count > 0:
                    summary['by_level'][level.value] = count
            return summary

# 全局实例
_enhanced_debug = EnhancedDebugVars()

# 便捷函数
def set_debug_var(key: str, value: Any, 
                  level: DebugLevel = DebugLevel.INFO,
                  category: DebugCategory = DebugCategory.STATUS,
                  description: str = "") -> None:
    """设置调试变量的便捷函数"""
    _enhanced_debug.set_var(key, value, level, category, description)

def set_debug_image(key: str, image: Any, description: str = "") -> None:
    """设置调试图像的便捷函数"""
    _enhanced_debug.set_image(key, image, description)

def get_debug_vars() -> Dict[str, Any]:
    """获取调试变量的便捷函数（兼容原接口）"""
    entries = _enhanced_debug.get_all_vars()
    return {k: v.value for k, v in entries.items()}

def get_debug_images() -> Dict[str, Any]:
    """获取调试图像的便捷函数（兼容原接口）"""
    entries = _enhanced_debug.get_all_images()
    return {k: v.image for k, v in entries.items()}

def get_enhanced_vars() -> Dict[str, DebugEntry]:
    """获取增强版调试变量"""
    return _enhanced_debug.get_all_vars()

def get_enhanced_images() -> Dict[str, DebugImageEntry]:
    """获取增强版调试图像"""
    return _enhanced_debug.get_all_images()

def reset_debug_vars() -> None:
    """重置所有调试变量"""
    _enhanced_debug.clear_all()

# 快捷设置函数
def set_status(key: str, value: Any, description: str = "") -> None:
    """设置状态变量"""
    set_debug_var(key, value, DebugLevel.INFO, DebugCategory.STATUS, description)

def set_error(key: str, value: Any, description: str = "") -> None:
    """设置错误变量"""
    set_debug_var(key, value, DebugLevel.ERROR, DebugCategory.ERROR, description)

def set_position(key: str, value: Any, description: str = "") -> None:
    """设置位置变量"""
    set_debug_var(key, value, DebugLevel.INFO, DebugCategory.POSITION, description)

def set_detection(key: str, value: Any, description: str = "") -> None:
    """设置检测变量"""
    set_debug_var(key, value, DebugLevel.INFO, DebugCategory.DETECTION, description)

def get_debug_summary() -> Dict[str, Any]:
    """获取调试汇总"""
    return _enhanced_debug.export_summary()