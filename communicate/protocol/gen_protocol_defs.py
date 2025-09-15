#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 variables.yaml 读取 (变量名, 变量类型)：
- 为每个变量名分配稳定的 1B ID（FNV-1a 8-bit；碰撞自动规避）
- 基于当前 UTC 秒级时间生成数据层版本号
- 生成 Python 与 C 的协议定义文件

生成物：
- protocol_defs.py
    PROTOCOL_DATA_VER_FULL: int = YYYYMMDDHHMMSS (UTC)
    PROTOCOL_DATA_VER     : int = (PROTOCOL_DATA_VER_FULL & 0xFF)
    Msg(IntEnum)          : PC_TO_MCU, MCU_TO_PC
    Var(IntEnum)          : 变量名 -> 稳定 ID（0x01..0xEF）
    VAR_META              : { vid: {"key": <yaml-name>, "vtype": <str>, "size": <int|None>} }
    VAR_FIXED_SIZE        : {int(Var.*): 固定字节数}（BYTES 不进入此表）

- protocol_c/data_defs.h
    #define PROTOCOL_DATA_VER_FULL  YYYYMMDDHHMMSSULL
    #define PROTOCOL_DATA_VER       0x??
    #define MSG_PC_TO_MCU           0x01
    #define MSG_MCU_TO_PC           0x02
    #define VAR_<NAME>              0x??
    #define VAR_<NAME>_SIZE         <N>    // 仅固定宽度变量生成
    static const uint8_t VAR_SIZE_TABLE[256] = { [VAR_X]=N, ... }; // 未声明者为 0

YAML 输入（二选一）:
1) 列表：
    variables:
      - name: test_var_u8
        vtype: U8
      - name: test_var_u16
        vtype: U16LE
2) 字典：
    variables_map:
      test_var_u8: U8
      test_var_u16: U16LE
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Optional

try:
    import yaml
except ImportError:
    print("Please `pip install pyyaml`", file=sys.stderr)
    sys.exit(1)

# 路径（脚本与 variables.yaml、输出文件位于同一目录）
ROOT = Path(__file__).resolve().parent
SPEC = ROOT / "variables.yaml"
PY_DIR = ROOT / "protocol_py"
PY_OUT = PY_DIR / "protocol_defs.py"
C_DIR = ROOT / "protocol_c"
C_OUT = C_DIR / "protocol_defs.h"

# 预留与类型定义
RESERVED_IDS = set([0x00]) | set(range(0xF0, 0x100))  # 保留：0x00 与 0xF0..0xFF
ID_SPACE_MIN = 0x01
ID_SPACE_MAX = 0xEF  # 含
# 固定宽度：字节数；BYTES 为 None 表示可变长（由 TLV 的 L 决定）
VALID_TYPES: Dict[str, Optional[int]] = {
    # ---- 基础与别名（固定 1 字节）----
    "U8": 1, "I8": 1, "BOOL": 1, "BYTE": 1,

    # ---- 16-bit ----
    "U16LE": 2, "I16LE": 2, "U16BE": 2, "I16BE": 2,
    # 宽松别名（默认按 LE 处理，若不想宽松可删除这两项）
    "U16": 2, "I16": 2,

    # ---- 32-bit ----
    "U32LE": 4, "I32LE": 4, "U32BE": 4, "I32BE": 4,
    "F32LE": 4, "F32BE": 4,
    # 宽松别名（默认按 LE 处理）
    "U32": 4, "I32": 4, "F32": 4,

    # ---- 可变长（由 TLV 的 L 决定）----
    "BYTES": None, "STR": None, "STRING": None, "UTF8": None, "ASCII": None,
}

# -------- FNV-1a 8-bit（稳定且简单）--------
def fnv1a8(s: str, salt: int = 0) -> int:
    # 8-bit FNV-1a：offset basis 0xCB, prime 0x1B（任选，只要稳定）
    h = (0xCB ^ (salt & 0xFF)) & 0xFF
    for ch in s.encode("utf-8"):
        h ^= ch
        h = (h * 0x1B) & 0xFF
    return h

def assign_ids(names: List[str]) -> Dict[str, int]:
    """
    为变量名分配 0x01..0xEF 的稳定 ID：
    - 先按变量名字典序遍历，确保确定性
    - 首选 hash；冲突则更换 salt 再 hash；极端情况下线性探测空位
    """
    used = set(RESERVED_IDS)
    out: Dict[str, int] = {}

    for name in sorted(names):
        found = None
        for salt in range(256):
            hid = fnv1a8(name, salt)
            if hid < ID_SPACE_MIN or hid > ID_SPACE_MAX or hid in used:
                continue
            found = hid
            break
        if found is None:
            for cand in range(ID_SPACE_MIN, ID_SPACE_MAX + 1):
                if cand not in used:
                    found = cand
                    break
        if found is None:
            raise RuntimeError("ID pool exhausted; adjust RESERVED_IDS or reduce variables.")
        used.add(found)
        out[name] = found
    return out

def load_variables() -> List[Tuple[str, str, str]]:
    """
    返回: List[(enum_name, vtype, key_name)]
    - enum_name: 大写（作为 Var 的枚举名）
    - key_name : YAML 内原始变量名（建议下划线小写），用于 UI 显示和业务键
    - vtype    : 规范化大写类型字符串
    """
    if not SPEC.exists():
        raise FileNotFoundError(f"spec file not found: {SPEC}")

    doc = yaml.safe_load(SPEC.read_text(encoding="utf-8")) or {}

    items: List[Tuple[str, str, str]] = []
    if "variables" in doc and doc["variables"]:
        for item in doc["variables"]:
            key = str(item["name"]).strip()
            enum_name = key.strip().upper()
            vtype = str(item["vtype"]).strip().upper()
            items.append((enum_name, vtype, key))
    if "variables_map" in doc and doc["variables_map"]:
        for key, vtype in doc["variables_map"].items():
            key = str(key).strip()
            enum_name = key.upper()
            items.append((enum_name, str(vtype).strip().upper(), key))

    if not items:
        raise ValueError("no variables found; fill `variables` or `variables_map` in YAML")

    # 去重 + 类型校验（按 enum_name 去重）
    seen = set()
    cleaned: List[Tuple[str, str, str]] = []
    for enum_name, vtype, key in items:
        if enum_name in seen:
            raise ValueError(f"duplicated variable name: {enum_name}")
        if vtype not in VALID_TYPES:
            raise ValueError(f"unknown vtype '{vtype}' for variable {enum_name}. "
                             f"Valid: {sorted(VALID_TYPES.keys())}")
        seen.add(enum_name)
        cleaned.append((enum_name, vtype, key))
    return cleaned

def build_time_versions() -> tuple[int, int]:
    """
    生成秒级版本：
    - PROTOCOL_DATA_VER_FULL = YYYYMMDDHHMMSS (UTC)
    - PROTOCOL_DATA_VER      = PROTOCOL_DATA_VER_FULL & 0xFF (1 字节写入 DATA 头)
    """
    now = datetime.now(timezone.utc)
    full = int(now.strftime("%Y%m%d%H%M%S"))  # 例如 20250903142517
    short = full & 0xFF
    return full, short

# ---------- Python 输出 ----------
def gen_protocol_defs_py(vars_list: List[Tuple[str, str, str]]) -> str:
    # vars_list: (ENUM_NAME, VTYPE, KEY_NAME)
    names = [enum_name for enum_name, _, _ in vars_list]
    id_map = assign_ids(names)

    # 固定宽度表
    fixed_items = []
    for enum_name, vtype, _ in vars_list:
        size = VALID_TYPES[vtype]
        if size is not None:
            fixed_items.append((enum_name, id_map[enum_name], size))

    # VAR_META：vid -> {"key": key_name, "vtype": vtype, "size": size or None}
    meta_items = []
    for enum_name, vtype, key_name in vars_list:
        vid = id_map[enum_name]
        size = VALID_TYPES[vtype]
        meta_items.append((enum_name, vid, key_name, vtype, size))

    full_ver, short_ver = build_time_versions()

    lines: List[str] = []
    lines.append("# Auto-generated. DO NOT EDIT MANUALLY.")
    lines.append(f"# Generated at UTC {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("# Version policy:")
    lines.append("#   PROTOCOL_DATA_VER_FULL = YYYYMMDDHHMMSS (UTC)")
    lines.append("#   PROTOCOL_DATA_VER      = PROTOCOL_DATA_VER_FULL & 0xFF  # 1-byte for DATA header")
    lines.append("")
    lines.append("from enum import IntEnum")
    lines.append("from typing import Dict, Optional, TypedDict")
    lines.append("")
    lines.append(f"PROTOCOL_DATA_VER_FULL: int = {full_ver}")
    lines.append(f"PROTOCOL_DATA_VER: int = 0x{short_ver:02X}")
    lines.append("")
    lines.append("class Msg(IntEnum):")
    lines.append("    PC_TO_MCU = 0x01")
    lines.append("    MCU_TO_PC = 0x02")
    lines.append("")
    lines.append("class Var(IntEnum):")
    # 以 ID 顺序输出，便于 MCU 查表/阅读
    for enum_name, _, _ in sorted(vars_list, key=lambda x: id_map[x[0]]):
        vid = id_map[enum_name]
        vtype = next(v for n, v, _ in vars_list if n == enum_name)
        lines.append(f"    {enum_name} = 0x{vid:02X}  # {vtype}")
    lines.append("")
    lines.append("class VarMeta(TypedDict, total=False):")
    lines.append("    key: str       # 原始键（YAML 中的 name，用于 UI/业务）")
    lines.append("    vtype: str     # 变量类型字符串（如 U16LE/F32/…）")
    lines.append("    size: Optional[int]  # 固定长度；可变长(BYTES/STR/…)为 None")
    lines.append("")
    lines.append("VAR_META: Dict[int, VarMeta] = {")
    for enum_name, vid, key_name, vtype, size in sorted(meta_items, key=lambda x: x[1]):
        key_s = key_name.replace('\\', '\\\\').replace('"', '\\"')
        lines.append(f'    int(Var.{enum_name}): {{"key": "{key_s}", "vtype": "{vtype}", "size": {repr(size)}}},')
    lines.append("}")
    lines.append("")
    lines.append("VAR_FIXED_SIZE: Dict[int, int] = {")
    for enum_name, vid, size in sorted(fixed_items, key=lambda x: x[1]):
        lines.append(f"    int(Var.{enum_name}): {size},")
    lines.append("}")
    lines.append("")
    lines.append("# 说明：")
    lines.append("# - BYTES/STR 等可变长类型不在 VAR_FIXED_SIZE 中；按 TLV 的 L 解析。")
    lines.append("# - 编解码逻辑由其他模块实现；此文件仅提供 ID/类型/长度元信息。")
    return "\n".join(lines) + "\n"

# ---------- C 输出 ----------
def gen_c_header(vars_list: List[Tuple[str, str, str]]) -> str:
    # vars_list: (ENUM_NAME, VTYPE, KEY_NAME)
    names = [enum_name for enum_name, _, _ in vars_list]
    id_map = assign_ids(names)
    full_ver, short_ver = build_time_versions()

    # 固定宽度
    fixed = {enum_name: VALID_TYPES[vtype] for enum_name, vtype, _ in vars_list if VALID_TYPES[vtype] is not None}

    lines: List[str] = []
    lines.append("// Auto-generated. DO NOT EDIT MANUALLY.")
    lines.append(f"// Generated at UTC {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("#ifndef PROTOCOL_DEFS_H")
    lines.append("#define PROTOCOL_DEFS_H")
    lines.append("#include <stdint.h>")
    lines.append("")
    lines.append(f"#define PROTOCOL_DATA_VER_FULL  {full_ver}ULL")
    lines.append(f"#define PROTOCOL_DATA_VER       0x{(full_ver & 0xFF):02X}")
    lines.append("")
    lines.append("// MSG roles")
    lines.append("#define MSG_PC_TO_MCU 0x01")
    lines.append("#define MSG_MCU_TO_PC 0x02")
    lines.append("")
    lines.append("// Variable IDs (T in TLV)")
    for enum_name, _, _ in sorted(vars_list, key=lambda x: id_map[x[0]]):
        lines.append(f"#define VAR_{enum_name} 0x{id_map[enum_name]:02X}")
    lines.append("")
    lines.append("// Fixed sizes (only for fixed-width variables); others are variable-length per TLV L")
    for enum_name, size in sorted(fixed.items(), key=lambda x: id_map[x[0]]):
        lines.append(f"#define VAR_{enum_name}_SIZE {size}")
    lines.append("")
    # 生成 256 项尺寸查表（未声明者为 0）
    lines.append("static const uint8_t VAR_SIZE_TABLE[256] = {")
    for enum_name, size in sorted(fixed.items(), key=lambda x: id_map[x[0]]):
        lines.append(f"    [VAR_{enum_name}] = {size},")
    lines.append("    // others default to 0 (variable-length)")
    lines.append("};")
    lines.append("")
    lines.append("#endif // PROTOCOL_DEFS_H")
    lines.append("")
    return "\n".join(lines) + "\n"

def main():
    vars_list = load_variables()  # List[(ENUM_NAME, VTYPE, KEY_NAME)]

    # Python
    PY_DIR.mkdir(parents=True, exist_ok=True)
    PY_OUT.write_text(gen_protocol_defs_py(vars_list), encoding="utf-8")
    print(f"wrote {PY_OUT}")

    # C
    C_DIR.mkdir(parents=True, exist_ok=True)
    C_OUT.write_text(gen_c_header(vars_list), encoding="utf-8")
    print(f"wrote {C_OUT}")

if __name__ == "__main__":
    main()
