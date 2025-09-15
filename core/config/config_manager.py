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

# ---------- 类型工具 ----------
def _is_dataclass_type(tp: Any) -> bool:
    return isinstance(tp, type) and is_dataclass(tp)

def _is_optional(ann: Any) -> bool:
    origin = get_origin(ann)
    if origin is Union:
        args = get_args(ann)
        return any(a is type(None) for a in args)
    return False

def _strip_optional(ann: Any) -> Any:
    origin = get_origin(ann)
    if origin is Union:
        args = tuple(a for a in get_args(ann) if a is not type(None))
        if len(args) == 1:
            return args[0]
        return Union[args]  # type: ignore
    return ann

def _empty_value_for(ann: Any) -> Any:
    """
    为“缺失字段”提供一个合理的留空值：
    - Optional[...]  -> None
    - 容器类型        -> 空容器
    - 其他标量/自定义 -> None（留空）
    """
    if _is_optional(ann):
        return None
    origin = get_origin(ann)
    args = get_args(ann)

    if origin in (list, List, Sequence):
        return []
    if origin in (dict, Dict):
        return {}
    if origin in (tuple, Tuple):
        return tuple()
    if _is_dataclass_type(ann):
        # 嵌套 dataclass：全部留空（递归构造）
        try:
            return _build_dataclass_forgiving(ann, {})
        except Exception:
            return None
    # 标量等默认 None
    return None

# ---------- 兼容性校验（只校验已存在字段） ----------
def _is_compatible(value: Any, ann: Any) -> bool:
    if ann is Any:
        return True
    origin = get_origin(ann)
    args = get_args(ann)

    if origin is None:
        if ann is type(None):
            return value is None
        if _is_dataclass_type(ann):
            return isinstance(value, dict)
        if isinstance(ann, type):
            return isinstance(value, ann)
        return True
    if origin is Union:
        return any(_is_compatible(value, a) for a in args)
    if origin in (list, List, Sequence):
        if not isinstance(value, list):
            return False
        inner = args[0] if args else Any
        return all(_is_compatible(v, inner) for v in value)
    if origin in (dict, Dict):
        if not isinstance(value, dict):
            return False
        kt, vt = args if len(args) == 2 else (Any, Any)
        return all(_is_compatible(k, kt) and _is_compatible(v, vt) for k, v in value.items())
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
            return _build_dataclass_forgiving(ann, value)
        return value
    if origin is Union:
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

# ---------- 宽松构造 ----------
def _build_dataclass_forgiving(cls: Type[T], data: dict) -> T:
    """
    宽松构造 dataclass：
    - 只使用 cls 字段（忽略 data 中的多余键）
    - 缺失字段：default/default_factory/Optional->None/否则None（留空）
    - 嵌套/容器：递归宽松处理
    """
    kwargs = {}
    for f in fields(cls):
        if f.name in data:
            raw = data[f.name]
            try:
                kwargs[f.name] = _convert_value(f.type, raw)
            except Exception as e:
                logger.warning(f'字段 {f.name} 转换失败，使用留空值: {e}')
                kwargs[f.name] = _empty_value_for(f.type)
        else:
            if f.default is not MISSING:
                kwargs[f.name] = f.default
            elif f.default_factory is not MISSING:  # type: ignore
                kwargs[f.name] = f.default_factory()  # type: ignore
            else:
                # 无默认：按“留空”策略
                kwargs[f.name] = _empty_value_for(f.type)
                logger.debug(f'字段 {f.name} 缺失，设置为留空值 {kwargs[f.name]!r}')
    return cls(**kwargs)

def _validate_config_forgiving(data: dict, cls: Type[T]) -> None:
    """
    宽松校验：只校验“存在”的字段类型形状。
    缺失字段不报错，交给构造阶段补齐留空/默认。
    """
    if not isinstance(data, dict):
        raise TypeError(f'配置根类型必须是对象(dict)，实际是 {type(data)}')

    field_map = {f.name: f for f in fields(cls)}
    for k, v in list(data.items()):
        if k not in field_map:
            # 忽略多余字段，但给个 debug
            logger.debug(f'忽略未知字段: {k}')
            continue
        f = field_map[k]
        if not _is_compatible(v, f.type):
            raise TypeError(f'字段 {f.name} 类型不匹配: 期望 {f.type}, 实际 {type(v)}')

# ---------- 读取 ----------
def load_config(config_file: str, config_class: Type[T]) -> Optional[T]:
    """从文件加载配置到指定 dataclass；兼容不同版本：有值就用，缺失留空/默认。"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        _validate_config_forgiving(config_data, config_class)
        obj = _build_dataclass_forgiving(config_class, config_data)
        return obj
    except FileNotFoundError:
        logger.error(f'配置文件不存在: {config_file}')
        return None
    except Exception as e:
        logger.error(f'配置加载时出现错误: {e}')
        return None
