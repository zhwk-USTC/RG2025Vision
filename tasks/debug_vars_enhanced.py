import threading
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
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
    """增强版调试变量管理器"""
    
    def __init__(self, max_entries: int = 1000):
        self._variables: Dict[str, DebugEntry] = {}
        self._images: Dict[str, DebugImageEntry] = {}
        self._history: List[DebugEntry] = []
        self._lock = threading.Lock()
        self._max_entries = max_entries
        
    def set_var(self, key: str, value: Any, 
                level: DebugLevel = DebugLevel.INFO,
                category: DebugCategory = DebugCategory.STATUS,
                description: str = "") -> None:
        """设置调试变量"""
        with self._lock:
            entry = DebugEntry(key, value, datetime.now(), level, category, description)
            self._variables[key] = entry
            self._history.append(entry)
            
            # 限制历史记录长度
            if len(self._history) > self._max_entries:
                self._history = self._history[-self._max_entries:]
    
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
    
    def get_vars_by_category(self, category: DebugCategory) -> Dict[str, DebugEntry]:
        """按分类获取变量"""
        with self._lock:
            return {k: v for k, v in self._variables.items() if v.category == category}
    
    def get_vars_by_level(self, level: DebugLevel) -> Dict[str, DebugEntry]:
        """按级别获取变量"""
        with self._lock:
            return {k: v for k, v in self._variables.items() if v.level == level}
    
    def get_all_vars(self) -> Dict[str, DebugEntry]:
        """获取所有变量"""
        with self._lock:
            return dict(self._variables)
    
    def get_all_images(self) -> Dict[str, DebugImageEntry]:
        """获取所有图像"""
        with self._lock:
            return dict(self._images)
    
    def get_history(self, limit: int = 100) -> List[DebugEntry]:
        """获取历史记录"""
        with self._lock:
            return self._history[-limit:] if limit else self._history.copy()
    
    def clear_category(self, category: DebugCategory) -> None:
        """清除特定分类的变量"""
        with self._lock:
            keys_to_remove = [k for k, v in self._variables.items() if v.category == category]
            for key in keys_to_remove:
                del self._variables[key]
    
    def clear_all(self) -> None:
        """清除所有变量和图像"""
        with self._lock:
            self._variables.clear()
            self._images.clear()
    
    def export_summary(self) -> Dict[str, Any]:
        """导出汇总信息"""
        with self._lock:
            summary = {
                'total_vars': len(self._variables),
                'total_images': len(self._images),
                'by_category': {},
                'by_level': {},
                'latest_entries': [entry.to_dict() for entry in self._history[-10:]]
            }
            
            # 按分类统计
            for category in DebugCategory:
                count = sum(1 for v in self._variables.values() if v.category == category)
                if count > 0:
                    summary['by_category'][category.value] = count
            
            # 按级别统计
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