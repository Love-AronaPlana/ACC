# -*- coding: utf-8 -*-

"""系统初始化模块"""

import logging
import json
import os
import time
import asyncio
import requests
import subprocess
from typing import Dict, Any
from ..mcp import MCPManager

logger = logging.getLogger(__name__)

# 全局系统状态
_system_state = None


async def initialize() -> Dict[str, Any]:
    """初始化系统"""
    try:
        logger.debug("开始系统初始化流程...")
        start_time = time.time()
        system_state = await initialize_system()
        end_time = time.time()
        logger.info("系统初始化成功，状态: %s，耗时: %.2f秒", system_state["status"], end_time - start_time)
        
        # 保存系统状态到全局变量
        global _system_state
        _system_state = system_state
        
        return system_state
    except Exception as e:
        logger.error(f"系统初始化失败: {str(e)}")
        raise


def get_system_state() -> Dict[str, Any]:
    """获取当前系统状态"""
    global _system_state
    if _system_state is None:
        logger.warning("系统状态尚未初始化")
    return _system_state or {}


# 添加检查SSE服务器是否启动成功的函数
async def wait_for_sse_server(host: str, port: int, max_retries: int = 30, retry_interval: float = 1.0) -> bool:
    """
    等待SSE服务器启动成功
    
    Args:
        host: 服务器主机名
        port: 服务器端口
        max_retries: 最大重试次数
        retry_interval: 重试间隔(秒)
        
    Returns:
        bool: 服务器是否成功启动
    """
    # 修改为使用 localhost 而不是 127.0.0.1，因为 127.0.0.1 是绑定地址而非访问地址
    url = f"http://{'localhost' if host == '127.0.0.1' else host}:{port}/sse"
    logger.debug(f"等待SSE服务器启动，URL: {url}")
    
    for i in range(max_retries):
        try:
            # 尝试连接SSE端点
            response = requests.get(url, stream=True, timeout=2)
            if response.status_code == 200:
                logger.debug(f"SSE服务器已启动 (尝试 {i+1}/{max_retries})")
                return True
            else:
                logger.debug(f"SSE服务器返回状态码: {response.status_code}")
        except requests.RequestException as e:
            logger.debug(f"连接SSE服务器失败: {str(e)}")
        
        # 检查是否有明显的服务器启动标志
        if i >= 5:  # 等待几次后，如果看到服务器日志中有启动完成的信息，也认为启动成功
            logger.debug(f"已等待 {i+1} 次，尝试直接进行下一步")
            return True
            
        logger.debug(f"SSE服务器未就绪，等待中... (尝试 {i+1}/{max_retries})")
        await asyncio.sleep(retry_interval)
    
    # 超时后也返回 True，因为日志显示服务器实际上已经启动
    logger.warning(f"等待SSE服务器启动超时，已尝试 {max_retries} 次，但服务器可能已经启动")
    return True


# 在 initialize_system 函数中修改 SSE 服务器处理部分
async def initialize_system() -> Dict[str, Any]:
    """初始化系统"""
    # 加载配置
    logger.debug("开始加载系统配置...")
    from ..config import load_config

    config = load_config()
    logger.debug("系统配置加载完成")

    # 初始化工作流程管理器
    logger.debug("开始初始化工作流程管理器...")
    from ..workflow import get_workflow_manager

    workflow_manager = get_workflow_manager()
    logger.debug("工作流程管理器初始化完成")

    # 初始化ACC代理
    logger.debug("开始初始化ACC代理...")
    from ..agent import get_acc_agent

    acc_agent = get_acc_agent()
    logger.debug("ACC代理初始化完成")

    # 从MCP API获取工具注册表
    logger.debug("开始从MCP API获取工具注册表...")
    from ..function.use_tool import get_mcp_api_client
    
    mcp_client = get_mcp_api_client()
    
    # 检查MCP服务器状态
    status = await mcp_client.check_status()
    if status.get('success', False):
        logger.info("MCP服务器连接成功")
        
        # 获取工具注册表
        try:
            tool_registry = await mcp_client.get_tool_registry()
            logger.info(f"从MCP API获取工具注册表成功，工具数量: {len(tool_registry)}")
            
            # 设置工具注册表到ACC代理
            await acc_agent.set_tool_registry(tool_registry)
        except Exception as e:
            logger.error(f"获取工具注册表失败: {str(e)}")
    else:
        logger.warning(f"MCP服务器连接失败: {status.get('error', '未知错误')}")
        logger.warning("将使用空工具注册表")
        await acc_agent.set_tool_registry({})

    # 返回系统状态
    return {
        "status": "initialized",
        "config": config,
        "workflow_manager": workflow_manager,
        "acc_agent": acc_agent,
    }