# -*- coding: utf-8 -*-

"""
打印信息模块

该模块负责将信息直接打印给用户并处理用户输入
"""

import json
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


def print_for_user(message: str) -> Dict[str, Any]:
    """将信息直接打印给用户

    Args:
        message: 要打印给用户的信息

    Returns:
        包含状态信息的字典
    """
    logger.debug(f"打印信息给用户: {message}")

    # 直接打印信息给用户
    print(f"\n{message}")

    # 返回操作状态
    return {
        "status": "success",
        "message": "信息已成功打印给用户",
        "content": message,
        "type": "response"  # 添加type字段
    }


def handle_print_for_user(message: str, get_input_func=None) -> Tuple[Dict[str, Any], str]:
    """处理打印信息并获取用户输入
    
    Args:
        message: 要打印给用户的信息
        get_input_func: 获取用户输入的函数
        
    Returns:
        包含状态信息的字典和用户输入
    """
    # 打印信息给用户
    result = print_for_user(message)
    
    # 等待用户输入下一条命令
    logger.debug("等待用户输入下一条命令")
    if get_input_func:
        user_input = get_input_func()
    else:
        # 使用统一的输入函数，从cli模块导入
        from ..interaction.cli import get_user_input as cli_get_input
        user_input = cli_get_input()
    
    return result, user_input


def format_message(message_data: Dict[str, Any]) -> str:
    """格式化消息数据

    Args:
        message_data: 消息数据字典

    Returns:
        格式化后的消息字符串
    """
    if isinstance(message_data, str):
        return message_data

    try:
        if isinstance(message_data, dict):
            # 如果是字典，尝试格式化为更友好的输出
            return json.dumps(message_data, ensure_ascii=False, indent=2)
        else:
            # 其他类型直接转为字符串
            return str(message_data)
    except Exception as e:
        logger.error(f"格式化消息时出错: {str(e)}")
        return str(message_data)
