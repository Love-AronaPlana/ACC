# -*- coding: utf-8 -*-

"""ACC工作流程控制模块

该模块负责控制ACC系统的主要工作流程，包括：
- 初始化系统组件
- 处理执行结果
- 管理系统状态等
"""

import logging
import os
from typing import Dict, Any, List, Optional

from ACC.config import get_value
from ACC.llm import send_message
from ACC.prompt import SYSTEM_PROMPT  # 添加导入SYSTEM_PROMPT

# 配置日志记录器
logger = logging.getLogger(__name__)


class WorkflowManager:
    """工作流程管理器，负责控制系统工作流程"""

    def __init__(self):
        """初始化工作流程管理器"""
        # 初始化系统状态
        self.status = "ready"
        self.current_step = 0
        self.workspace_path = get_value("workspace", "default_path")
        self.debug = get_value("llm", "debug", False)  # 正确获取debug配置
        # 初始化工具列表属性
        self.tools = []

        if self.debug:
            logger.debug("工作流程调试模式已启用")  # 添加的调试确认语句
            logger.debug(
                f"工作流程管理器初始化完成，工作空间路径: {self.workspace_path}"
            )

        # 确保工作空间目录存在
        self._ensure_workspace()

        logger.info("工作流程管理器初始化完成")

    def _ensure_workspace(self):
        """确保工作空间目录存在"""
        # 获取工作空间的绝对路径
        if not os.path.isabs(self.workspace_path):
            self.workspace_path = os.path.abspath(self.workspace_path)

        # 如果目录不存在，则创建
        if not os.path.exists(self.workspace_path):
            os.makedirs(self.workspace_path)
            logger.info(f"创建工作空间目录: {self.workspace_path}")

    def start(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        user_status: str = "user_message",
    ) -> Dict[str, Any]:
        """启动工作流程

        Args:
            user_input: 用户输入
            system_prompt: 可选的自定义系统提示词
            user_status: 用户状态名称，默认为"user_message"

        Returns:
            工作流程结果
        """
        # 使用自定义系统提示词或默认提示词
        prompt = system_prompt or SYSTEM_PROMPT

        # 发送消息到LLM，添加用户状态参数
        response = send_message(prompt, user_input, self.tools, user_status=user_status)

        return response

    def execute_step(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流程步骤

        Args:
            step_data: 步骤数据

        Returns:
            步骤执行结果
        """
        # 更新当前步骤
        self.current_step = step_data.get("step", self.current_step + 1)

        # 记录步骤信息
        logger.info(f"执行步骤 {self.current_step}: {step_data.get('status', '')}")

        # 返回步骤数据
        return step_data


# 全局工作流程管理器实例
_workflow_manager = None


def get_workflow_manager() -> WorkflowManager:
    """获取工作流程管理器实例

    Returns:
        工作流程管理器实例
    """
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = WorkflowManager()
    return _workflow_manager
