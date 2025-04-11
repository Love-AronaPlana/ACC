# -*- coding: utf-8 -*-

"""ACC基础模块

该模块负责：
1. 提供系统基础配置
2. 初始化必要的系统组件
3. 提供系统级的工具函数
"""

import logging
import os
from typing import Dict, Any

from ACC import load_config, get_config
from ACC.agent import get_acc_agent
from ACC.workflow import get_workflow_manager

# 配置日志记录器
logger = logging.getLogger(__name__)


def initialize_system() -> Dict[str, Any]:
    """初始化系统

    Returns:
        系统状态字典
    """
    # 加载配置
    config = load_config()
    logger.info("配置加载成功")

    # 初始化工作流程管理器
    workflow_manager = get_workflow_manager()
    logger.info("工作流程管理器初始化成功")

    # 初始化ACC代理
    acc_agent = get_acc_agent()
    logger.info("ACC代理初始化成功")

    # 返回系统状态
    return {
        "config": config,
        "workflow_manager": workflow_manager,
        "acc_agent": acc_agent,
        "status": "ready",
    }


def get_workspace_path() -> str:
    """获取工作空间路径

    Returns:
        工作空间绝对路径
    """
    # 从配置中获取工作空间路径
    workspace_path = get_config()["workspace"]["default_path"]

    # 如果是相对路径，转换为绝对路径
    if not os.path.isabs(workspace_path):
        workspace_path = os.path.abspath(workspace_path)

    return workspace_path
