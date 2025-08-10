#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 文件名: cleanup.py
# 描述: 一键删除项目中的临时文件

import os
import shutil
import glob
import logging

def cleanup_temp_files():
    """删除项目中的临时文件"""
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    logger = logging.getLogger()
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 计数器
    deleted_dirs = 0
    deleted_files = 0
    
    # 删除所有 __pycache__ 目录
    for root, dirs, _ in os.walk(current_dir):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            try:
                shutil.rmtree(pycache_path)
                logger.info(f"已删除: {pycache_path}")
                deleted_dirs += 1
            except Exception as e:
                logger.error(f"无法删除 {pycache_path}: {e}")
    
    # 删除所有 .pyc 文件
    for pyc_file in glob.glob(os.path.join(current_dir, '**/*.pyc'), recursive=True):
        try:
            os.remove(pyc_file)
            logger.info(f"已删除: {pyc_file}")
            deleted_files += 1
        except Exception as e:
            logger.error(f"无法删除 {pyc_file}: {e}")
    
    # 总结
    logger.info(f"清理完成! 已删除 {deleted_dirs} 个目录和 {deleted_files} 个文件")

if __name__ == "__main__":
    cleanup_temp_files()