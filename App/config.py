"""
全局配置管理模块

支持配置数据源（BAO_STOCK或QMTAPI）等全局设置
"""
import os
import json
from pathlib import Path
from typing import Optional
import streamlit as st

from Common.CEnum import DATA_SRC


# 配置文件路径 - 放在当前目录（App目录）下
CONFIG_FILE = Path(__file__).resolve().parent / "config.json"


def ensure_config_dir():
    """确保配置目录存在（当前目录已存在，无需创建）"""
    pass


def get_default_config() -> dict:
    """获取默认配置"""
    return {
        "data_source": "BAO_STOCK",  # 默认使用BAO_STOCK
        "data_source_custom": "custom:QMTAPI.CQMTAPI",  # QMTAPI的自定义格式
    }


def load_config() -> dict:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置，确保所有字段都存在
                default_config = get_default_config()
                default_config.update(config)
                return default_config
        except Exception as e:
            print(f"Failed to load config: {e}")
            return get_default_config()
    else:
        return get_default_config()


def save_config(config: dict):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save config: {e}")


def get_data_source() -> str:
    """
    获取当前配置的数据源（字符串格式，用于配置文件存储）
    
    Returns:
        str: 数据源字符串，'BAO_STOCK'或'custom:QMTAPI.CQMTAPI'等
    """
    # 优先从session_state获取（用于Streamlit应用）
    if hasattr(st, 'session_state') and 'app_data_source' in st.session_state:
        data_source = st.session_state.app_data_source
        # 如果是DATA_SRC枚举，转换为字符串
        if isinstance(data_source, DATA_SRC):
            if data_source == DATA_SRC.BAO_STOCK:
                return "BAO_STOCK"
            else:
                return str(data_source)
        return str(data_source)
    
    # 从配置文件获取
    config = load_config()
    data_source = config.get("data_source", "BAO_STOCK")
    
    # 确保返回的是字符串格式
    if isinstance(data_source, DATA_SRC):
        if data_source == DATA_SRC.BAO_STOCK:
            return "BAO_STOCK"
        else:
            return str(data_source)
    
    return str(data_source)


def set_data_source(data_source: str):
    """
    设置数据源
    
    Args:
        data_source: 数据源字符串，'BAO_STOCK'或'QMTAPI'
    """
    config = load_config()
    
    if data_source == "QMTAPI":
        config["data_source"] = "custom:QMTAPI.CQMTAPI"
        data_source_value = "custom:QMTAPI.CQMTAPI"
    elif data_source == "BAO_STOCK":
        config["data_source"] = "BAO_STOCK"
        data_source_value = DATA_SRC.BAO_STOCK  # session_state存储枚举
    else:
        # 允许直接设置自定义格式
        config["data_source"] = data_source
        data_source_value = data_source
    
    save_config(config)
    
    # 同时更新session_state（如果可用）
    # BAO_STOCK存储为枚举，QMTAPI存储为字符串
    if hasattr(st, 'session_state'):
        st.session_state.app_data_source = data_source_value


def get_data_source_for_chan():
    """
    获取用于CChan初始化的数据源
    
    Returns:
        可以直接用于CChan的data_src参数的值
        - BAO_STOCK: 返回 DATA_SRC.BAO_STOCK 枚举
        - QMTAPI: 返回字符串 'custom:QMTAPI.CQMTAPI'
    """
    # 优先从session_state获取（可能已经是枚举类型）
    if hasattr(st, 'session_state') and 'app_data_source' in st.session_state:
        data_source = st.session_state.app_data_source
        # 如果已经是枚举类型，直接返回
        if isinstance(data_source, DATA_SRC):
            return data_source
        # 如果是字符串，继续处理
        if isinstance(data_source, str):
            if data_source == "BAO_STOCK":
                return DATA_SRC.BAO_STOCK
            return data_source
    
    # 从配置文件获取（配置文件存储的是字符串）
    data_source = get_data_source()
    
    # 如果是BAO_STOCK字符串，返回DATA_SRC枚举
    if data_source == "BAO_STOCK":
        return DATA_SRC.BAO_STOCK
    
    # 如果是QMTAPI或其他自定义格式，直接返回字符串
    return data_source


def get_data_source_display_name() -> str:
    """
    获取数据源的显示名称
    
    Returns:
        str: 数据源的友好显示名称
    """
    data_source = get_data_source()
    
    if data_source == "BAO_STOCK" or data_source == DATA_SRC.BAO_STOCK:
        return "BaoStock"
    elif "QMTAPI" in str(data_source):
        return "QMT API"
    else:
        return str(data_source)
