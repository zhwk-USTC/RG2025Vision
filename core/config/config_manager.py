# config_io.py  （可替换你原来的函数）
import json
import os
import tempfile
from dataclasses import asdict, fields, is_dataclass, MISSING
from typing import Any, List, Optional, Sequence, Tuple, Type, TypeVar, Union, get_args, get_origin, Dict

from core.logger import logger

T = TypeVar('T')

# ---------- JSON 序列化 ----------
def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    # pydantic 兼容（可选）
    if hasattr(obj, 'model_dump'):
        try:
            return obj.model_dump()
        except Exception:
            pass
    if hasattr(obj, 'dict'):
        try:
            return obj.dict()
        except Exception:
            pass
    return obj

def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)

def save_config(config_file: str, config: Union[T, Sequence[T]]) -> None:
    try:
        data = _to_jsonable(config)
        _ensure_dir(config_file)

        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(config_file), prefix='.cfg.', suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush(); os.fsync(f.fileno())
            os.replace(tmp, config_file)
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
        logger.info(f'配置已成功保存到 {config_file}')
    except Exception as e:
        logger.error(f'保存配置时出现错误: {e}')

# ---------- 类型校验 & 构造 ----------
def _is_dataclass_type(tp: Any) -> bool:
    return isinstance(tp, type) and is_dataclass(tp)

def _is_compatible(value: Any, ann: Any) -> bool:
    if ann is Any:
        return True
    origin = get_origin(ann)
    args = get_args(ann)

    if origin is None:
        if ann is type(None):
            return value is None
        if _is_dataclass_type(ann):
            return isinstance(value, dict)  # 形状检查：后面会递归字段
        if isinstance(ann, type):
            return isinstance(value, ann)
        return True  # 不可判定的注解，放过
    # Union / Optional
    if origin is Union:
        return any(_is_compatible(value, a) for a in args)
    # List / Sequence
    if origin in (list, List, Sequence):
        if not isinstance(value, list):
            return False
        inner = args[0] if args else Any
        return all(_is_compatible(v, inner) for v in value)
    # Dict / Mapping
    if origin in (dict, Dict):
        if not isinstance(value, dict):
            return False
        kt, vt = args if len(args) == 2 else (Any, Any)
        return all(_is_compatible(k, kt) and _is_compatible(v, vt) for k, v in value.items())
    # Tuple
    if origin in (tuple, Tuple):
        if not isinstance(value, (list, tuple)):
            return False
        if len(args) == 2 and args[1] is Ellipsis:
            return all(_is_compatible(v, args[0]) for v in value)
        if len(value) != len(args):
            return False
        return all(_is_compatible(v, a) for v, a in zip(value, args))
    return True

def _convert_value(ann: Any, value: Any) -> Any:
    origin = get_origin(ann)
    args = get_args(ann)

    if ann is Any:
        return value
    if origin is None:
        if _is_dataclass_type(ann) and isinstance(value, dict):
            return _build_dataclass(ann, value)
        return value
    if origin is Union:
        # Optional/Union：选一个匹配的分支进行递归构造
        for a in args:
            if a is type(None) and value is None:
                return None
            if _is_compatible(value, a):
                return _convert_value(a, value)
        return value
    if origin in (list, List, Sequence):
        inner = args[0] if args else Any
        return [ _convert_value(inner, v) for v in (value or []) ]
    if origin in (dict, Dict):
        kt, vt = args if len(args) == 2 else (Any, Any)
        return { _convert_value(kt, k): _convert_value(vt, v) for k, v in (value or {}).items() }
    if origin in (tuple, Tuple):
        if len(args) == 2 and args[1] is Ellipsis:
            inner = args[0]
            return tuple(_convert_value(inner, v) for v in (value or []))
        return tuple(_convert_value(a, v) for a, v in zip(args, value))
    return value

def _build_dataclass(cls: Type[T], data: dict) -> T:
    kwargs = {}
    for f in fields(cls):
        if f.name in data:
            kwargs[f.name] = _convert_value(f.type, data[f.name])
        elif f.default is not MISSING:
            kwargs[f.name] = f.default
        elif f.default_factory is not MISSING:  # type: ignore
            kwargs[f.name] = f.default_factory()  # type: ignore
        else:
            raise ValueError(f'缺少必要字段: {f.name}')
    return cls(**kwargs)

def _validate_config(data: dict, cls: Type[T]) -> None:
    # 只做“字段存在 & 形状匹配”的校验；详细类型由 _is_compatible 处理
    for f in fields(cls):
        if f.name not in data:
            raise ValueError(f'缺少必要的字段: {f.name}')
        if not _is_compatible(data[f.name], f.type):
            raise TypeError(f'字段 {f.name} 类型不匹配: 期望 {f.type}, 实际 {type(data[f.name])}')

# ---------- 读取 ----------
def load_config(config_file: str, config_class: Type[T]) -> Optional[T]:
    """从文件加载配置并转换为指定的 dataclass（支持嵌套/容器类型）"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        _validate_config(config_data, config_class)
        obj = _build_dataclass(config_class, config_data)
        return obj
    except Exception as e:
        logger.error(f'配置加载时出现错误: {e}')
        return None
