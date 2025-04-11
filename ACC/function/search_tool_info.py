# -*- coding: utf-8 -*-

"""
工具搜索模块

该模块负责根据工具名称获取详细的工具调用信息
"""

import json
from typing import Dict, Optional
from ..agent import get_acc_agent
import logging

logger = logging.getLogger(__name__)


def get_tool_details(tool_name: str) -> Dict:
    """获取指定工具的详细信息"""
    logger.debug(f"开始搜索工具 - 目标名称: {tool_name}")
    agent = get_acc_agent()
    tool_registry = agent.tool_registry

    logger.debug(
        f"当前注册表工具数量: {len(tool_registry)} | 示例工具: {list(tool_registry.keys())[:3]}..."
    )

    # 遍历工具注册表查找匹配的工具
    found_tool = None
    for tool_key, tool_info in tool_registry.items():
        logger.debug(
            f"比对工具 - 注册名称: {tool_info['name']} | 目标名称: {tool_name}"
        )
        # 检查工具名称是否匹配（不考虑服务器前缀）
        if tool_info["name"] == tool_name:
            logger.debug(
                f"匹配成功 - 工具键: {tool_key} | 元数据: {json.dumps(tool_info, ensure_ascii=False, indent=2)}"
            )
            found_tool = tool_info
            break

    # 如果没有找到工具，返回错误信息
    if not found_tool:
        logger.warning(
            f"工具未找到 - 请求名称: {tool_name} | 可用工具列表: {list(set(t['name'] for t in tool_registry.values()))}"
        )
        return {"error": f"工具 {tool_name} 不存在"}

    # 构建标准化响应
    response = {
        "tool_name": found_tool["name"],
        "description": found_tool["description"],
        "parameters": found_tool["input_schema"],
        "allowed_directories": found_tool.get("allowed_paths", []),
    }

    # 确保所有JSON字符串都不包含Unicode转义
    if isinstance(response["description"], str):
        response["description"] = response["description"]
    if isinstance(response["parameters"], dict):
        # 将parameters转为JSON字符串再解析回来，确保内部没有Unicode转义
        response["parameters"] = json.loads(
            json.dumps(response["parameters"], ensure_ascii=False)
        )

    return response


def _format_tool_info(tool_info: Dict) -> Dict:
    """格式化工具信息（保留兼容性）"""
    formatted = {
        "name": tool_info["name"],
        "description": tool_info["description"],
        "parameters": tool_info.get("input_schema", {}),
        "allowed_directories": tool_info.get("allowed_paths", []),
    }

    # 确保所有JSON字符串都不包含Unicode转义
    if isinstance(formatted["parameters"], dict):
        formatted["parameters"] = json.loads(
            json.dumps(formatted["parameters"], ensure_ascii=False)
        )

    return formatted


def _generate_example(tool_info: Dict) -> Dict:
    """生成工具调用示例"""
    params = {}
    if "input_schema" in tool_info and "properties" in tool_info["input_schema"]:
        for param, schema in tool_info["input_schema"]["properties"].items():
            params[param] = f"<{schema.get('type', 'string')}>"

    return {"function": tool_info["name"], "arguments": params}
