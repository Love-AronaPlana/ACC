# -*- coding: utf-8 -*-

"""
用户输入处理模块

该模块负责获取用户输入并将其发送给LLM进行处理
"""

import json
import logging
from typing import Dict, Any
from ..interaction.cli import get_user_input as cli_get_input

logger = logging.getLogger(__name__)


def get_user_input(prompt: str) -> Dict[str, Any]:
    """获取用户输入并准备发送给LLM
    
    Args:
        prompt: 提示用户输入的信息
    
    Returns:
        包含用户输入和状态信息的字典
    """
    logger.debug(f"请求用户输入: {prompt}")
    
    # 打印提示信息
    print(f"\n{prompt}")
    print("(请连续按三次回车确认发送)")
    
    # 获取用户输入
    user_response = cli_get_input()
    
    logger.debug(f"用户输入: {user_response}")
    
    # 返回操作状态和用户输入
    return {
        "status": "success",
        "message": "已获取用户输入",
        "content": user_response,
        "user_status": "user_re_message",
    }


def format_user_input(user_input: str, original_prompt: str) -> Dict[str, Any]:
    """格式化用户输入为LLM可处理的格式

    Args:
        user_input: 用户输入的内容
        original_prompt: 原始提示内容

    Returns:
        格式化后的用户输入字典
    """
    return {
        "type": "user_response",
        "original_prompt": original_prompt,
        "user_input": user_input,
    }
