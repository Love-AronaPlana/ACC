# -*- coding: utf-8 -*-

"""ACC配置管理模块

该模块负责:
1. 加载系统配置文件
2. 提供配置访问接口
3. 验证配置有效性
"""

import os
import toml
from typing import Dict, Any, Optional, List

# 默认配置文件路径
DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "config.toml"
)

# 必需的配置项
REQUIRED_CONFIG = {
    "llm": ["model", "base_url", "api_key", "max_tokens"],
    "workspace": ["default_path"],
}

# 全局配置对象
_config: Dict[str, Any] = {}


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载配置文件

    Args:
        config_path: 配置文件路径，如果为None则使用默认路径

    Returns:
        配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误或缺少必要配置项
    """
    global _config

    # 使用默认路径或指定路径
    config_path = config_path or DEFAULT_CONFIG_PATH

    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    try:
        # 加载TOML配置文件
        _config = toml.load(config_path)

        # 验证必需的配置项
        validate_config(_config)

        return _config
    except toml.TomlDecodeError as e:
        raise ValueError(f"配置文件格式错误: {e}")


def validate_config(config: Dict[str, Any]) -> None:
    """验证配置是否包含所有必需的配置项

    Args:
        config: 配置字典

    Raises:
        ValueError: 缺少必要配置项
    """
    missing_sections = []
    missing_keys = []

    # 检查每个必需的配置部分
    for section, keys in REQUIRED_CONFIG.items():
        if section not in config:
            missing_sections.append(section)
            continue

        # 检查部分中的每个必需键
        for key in keys:
            if key not in config[section]:
                missing_keys.append(f"{section}.{key}")

    # 如果有缺失项，抛出异常
    if missing_sections or missing_keys:
        error_msg = ""
        if missing_sections:
            error_msg += f"缺少配置部分: {', '.join(missing_sections)}\n"
        if missing_keys:
            error_msg += f"缺少配置项: {', '.join(missing_keys)}"
        raise ValueError(error_msg)


def get_config() -> Dict[str, Any]:
    """获取当前配置

    Returns:
        配置字典
    """
    if not _config:
        load_config()
    return _config


def get_value(section: str, key: str, default: Any = None) -> Any:
    """获取指定配置项的值

    Args:
        section: 配置部分名称
        key: 配置项名称
        default: 默认值，如果配置项不存在则返回该值

    Returns:
        配置项的值
    """
    if not _config:
        load_config()

    try:
        return _config[section][key]
    except KeyError:
        return default
