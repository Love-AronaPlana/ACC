# -*- coding: utf-8 -*-

"""ACC代理核心模块"""

"""
该模块实现了ACC系统的代理功能，负责：
- 接收用户指令
- 执行相应操作
- 返回执行结果
"""

import logging
import json
import datetime  # 添加datetime模块导入
from typing import Dict, Any, List, Optional

from ..workflow import get_workflow_manager
from ..prompt import SYSTEM_PROMPT
from ..core.tool_discovery import ToolDiscovery

# 配置日志记录器
logger = logging.getLogger(__name__)


class ACCAgent:
    """ACC代理类，负责处理用户请求"""

    def __init__(self):
        """初始化ACC代理"""
        # 获取工作流程管理器
        self.workflow_manager = get_workflow_manager()
        # 初始化工具注册表
        self.tool_registry = {}
        logger.info("ACC代理初始化完成")

    def set_tool_registry(self, tool_registry: Dict[str, Dict[str, Any]]):
        """设置工具注册表

        Args:
            tool_registry: 工具注册表
        """
        self.tool_registry = tool_registry
        logger.info(f"已更新工具注册表，共 {len(self.tool_registry)} 个工具")

    def get_formatted_tools_list(self) -> str:
        """获取格式化的工具列表

        Returns:
            格式化的工具列表字符串
        """
        if not self.tool_registry:
            return "目前没有可用的工具。"

        tools_text = []
        for i, (tool_key, tool_info) in enumerate(self.tool_registry.items(), 1):
            # 检查是否为 sequentialthinking 工具，如果是则替换描述
            description = tool_info["description"]
            # if tool_info['name'] == "sequentialthinking":
            #     description = (
            #         "A detailed tool for dynamic and reflective problem-solving through thoughts.\n"
            #         "This tool helps analyze problems through a flexible thinking process that can adapt and evolve.\n"
            #         "Each thought can build on, question, or revise previous insights as understanding deepens."
            #     )

            tools_text.append(f"{i}. {tool_info['name']}: {description}")

        return "\n".join(tools_text)

    def _get_current_datetime(self) -> str:
        """获取当前日期时间（格式：年/月/日 时:分:秒）

        用于生成系统提示词中的时间戳，确保时间信息准确统一

        Returns:

            str: 格式化的日期时间字符串，例如'2023年10月05日 15时30分45秒'
        """
        now = datetime.datetime.now()
        return now.strftime("%Y年%m月%d日 %H时%M分%S秒")

    def get_system_prompt(self) -> str:
        """获取完整的系统提示词（包含工具列表、系统信息和用户名）"""
        # 获取基础信息
        system_info = self._get_system_info()
        user_name = self._get_user_name()
        tools_list = self.get_formatted_tools_list()
        date_time = self._get_current_datetime()  # 获取当前日期时间

        # 进行四重替换（添加日期时间替换）
        return (
            SYSTEM_PROMPT.replace("{system_info}", system_info)
            .replace("{user_name}", user_name)
            .replace("{tools_list}", tools_list)
            .replace("{date_time}", date_time)  # 替换日期时间占位符
        )

    def _get_system_info(self) -> str:
        """获取系统信息"""
        import platform

        return f"{platform.system()} {platform.release()} ({platform.version()})"

    def _get_user_name(self) -> str:
        """获取当前用户名"""
        import os
        from getpass import getuser

        return os.getenv("USERNAME") or os.getenv("USER") or getuser()

    def process_request(
        self, user_input: str, user_status: str = "user_message"
    ) -> Dict[str, Any]:
        """处理用户请求

        Args:
            user_input: 用户输入
            user_status: 用户状态名称，默认为"user_message"

        Returns:
            处理结果
        """
        # 记录用户请求
        logger.info(f"接收到用户请求: {user_input}")

        # 获取系统提示词
        system_prompt = self.get_system_prompt()

        # 确保系统提示词已添加到历史记录中
        from ..memory import get_history_manager

        history_manager = get_history_manager()
        history_manager.ensure_system_prompt(system_prompt)

        # 启动工作流程，传入替换了工具列表的系统提示词和用户状态
        response = self.workflow_manager.start(
            user_input, system_prompt=system_prompt, user_status=user_status
        )

        # 新增JSON提取逻辑
        if isinstance(response, dict) and "content" in response:
            content = response["content"]
            try:
                # 提取JSON代码块
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                json_str = content[json_start:json_end]
                json_data = json.loads(json_str)

                # 合并到响应字典
                response.update(
                    {
                        "function": json_data.get("function"),
                        "value": json_data.get("value"),
                        "tool_value": json_data.get("tool_value"),
                    }
                )

            except Exception as e:
                logger.error(f"JSON提取失败: {str(e)}")

        # 保持原有字段验证逻辑
        required_keys = ["function", "value"]
        if not all(key in response for key in required_keys):
            logger.error(f"响应缺少必要字段，现有字段: {response.keys()}")

        return response

    def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """处理工具调用"""
        tool_call = tool_calls[0]
        function = tool_call["function"]
        name = function["name"]
        arguments = function["arguments"]

        if name == "search_tool_info":
            from ..function.search_tool_info import get_tool_details

            tool_name = arguments.get("value")
            tool_info = get_tool_details(tool_name)

            # 修复点：返回结构需要包含tool_response类型
            return {
                "type": "tool_response",
                "name": name,
                "content": tool_info,
                "status": "tool_info",  # 确保这里使用 tool_info 作为状态
            }

        # 原有其他工具处理逻辑保持不变
        logger.info(f"工具调用: {name}, 参数: {arguments}")
        # 修复点：普通工具调用返回类型需要是tool_call
        return {"type": "tool_call", "name": name, "arguments": arguments}


# 全局ACC代理实例
_acc_agent = None


def get_acc_agent() -> ACCAgent:
    """获取ACC代理实例

    Returns:
        ACC代理实例
    """
    global _acc_agent
    if _acc_agent is None:
        _acc_agent = ACCAgent()
    return _acc_agent
