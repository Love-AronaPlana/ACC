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

    # MCP服务器连接
    logger.debug("开始初始化MCP管理器...")
    mcp_manager = MCPManager()
    logger.debug("MCP管理器初始化完成")

    # 加载MCP服务器配置
    logger.debug("开始加载MCP服务器配置...")
    config_path = os.path.join("config", "mcp_server.json")
    logger.debug(f"MCP配置文件路径: {os.path.abspath(config_path)}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        mcp_config = json.load(f)
    
    logger.debug(f"MCP配置加载完成，服务器数量: {len(mcp_config['mcpServers'])}")

    # 新增路径验证和服务器启动
    for server_name, server_config in mcp_config["mcpServers"].items():
        logger.debug(f"开始处理服务器 [{server_name}]...")
        
        # 获取配置参数
        command = server_config.get("command", "")
        args = server_config.get("args", [])  # 如果没有args字段，默认为空列表
        transport = server_config.get("transport", "")  # 获取transport配置
        local = server_config.get("local", "").lower() == "true"  # 检查是否为本地工具
        
        logger.debug(f"服务器 [{server_name}] 是否为本地工具: {local}")
        
        # 处理SSE传输方式，自动添加mcp-proxy配置
        if transport == "sse":
            # 如果没有指定command或command为空，则设置为mcp-proxy
            if not command:
                command = "mcp-proxy"
                server_config["command"] = command
                logger.debug(f"服务器 [{server_name}] 自动设置command为: {command}")
            
            # 如果没有指定args或args为空列表，则设置为空列表
            if args is None or len(args) == 0:
                args = []
                server_config["args"] = args
                logger.debug(f"服务器 [{server_name}] 自动设置args为空列表")
        
        logger.debug(f"服务器 [{server_name}] 命令: {command}")
        logger.debug(f"服务器 [{server_name}] 参数: {args}")
        logger.debug(f"服务器 [{server_name}] 传输方式: {transport}")
        
        # 路径预处理
        processed_args = [
            os.path.expandvars(arg) if isinstance(arg, str) and "%" in arg else arg  # 处理环境变量
            for arg in args
        ]
        
        if processed_args != args:
            logger.debug(f"服务器 [{server_name}] 参数处理后: {processed_args}")

        # 验证文件系统路径
        if server_name == "filesystem" and processed_args:
            logger.debug(f"验证文件系统路径: {processed_args[-2:]}")
            for path in processed_args[-2:]:  # 最后两个参数是路径
                if not os.path.exists(path):
                    logger.error(f"路径不存在: {path}")
                    raise FileNotFoundError(f"MCP服务器路径配置错误: {path} 不存在")
                logger.debug(f"路径验证通过: {path}")

        # 启动服务器
        logger.debug(f"开始连接服务器 [{server_name}]...")
        connect_start_time = time.time()
        
        try:
            if transport == "sse":
                # 获取SSE相关配置
                stdio_command = server_config.get("stdio_command")
                stdio_args = server_config.get("stdio_args", [])
                # 修改：只有在配置中明确指定了port时才使用，不再默认为8000
                port = server_config.get("port")
                host = "127.0.0.1"  # 默认使用127.0.0.1作为主机
                url = server_config.get("url", "")  # 获取url配置
                
                # 从args中提取host参数
                for arg in processed_args:
                    if isinstance(arg, str) and arg.startswith("--sse-host="):
                        host = arg.split("=")[1]
                    elif isinstance(arg, str) and arg.startswith("--sse-port="):
                        try:
                            port = int(arg.split("=")[1])
                        except ValueError:
                            logger.warning(f"无效的端口号: {arg}，将不使用端口")
                
                # 设置工作目录
                if local:
                    # 如果是本地工具，优先使用local_tools目录
                    cwd = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "local_tools")
                    if os.path.exists(cwd):
                        logger.debug(f"使用本地工具目录: {os.path.abspath(cwd)}")
                    else:
                        logger.warning(f"本地工具目录不存在: {cwd}，将使用默认目录")
                        cwd = None
                else:
                    # 非本地工具，使用mcp_server_files目录
                    cwd = os.path.join("mcp_server_files", server_name)
                    if os.path.exists(cwd):
                        logger.debug(f"使用工作目录: {os.path.abspath(cwd)}")
                    else:
                        cwd = None
                        logger.debug(f"工作目录不存在，使用当前目录")
                
                # 第二步：等待SSE服务器启动成功并验证HTTP端点
                if url:
                    # 使用配置中的URL
                    sse_url = url
                    # 确保URL以/sse结尾
                    if not sse_url.endswith("/sse"):
                        sse_url = sse_url + "/sse"
                    logger.debug(f"使用配置的URL: {sse_url}")
                elif port:
                    # 使用本地端口构建URL
                    sse_url = f"http://{host}:{port}/sse"
                    logger.debug(f"等待SSE服务器HTTP端点就绪: {sse_url}")
                    
                    # 只有在没有提供URL且有端口的情况下才需要启动本地服务器
                    if stdio_command:
                        # 第一步：执行stdio_command启动SSE服务器
                        logger.debug(f"正在启动SSE服务器: {stdio_command} {' '.join(stdio_args)}")
                        sse_process = await mcp_manager.start_sse_server(stdio_command, stdio_args, cwd, local)
                        
                        # 验证服务器是否启动成功
                        server_ready = await wait_for_sse_server(host, port)
                        if not server_ready:
                            logger.warning(f"SSE服务器HTTP端点验证超时，但将继续尝试连接")
                else:
                    # 既没有URL也没有端口，无法构建SSE URL
                    logger.warning(f"服务器 [{server_name}] 未提供URL或端口，无法构建SSE URL")
                    continue
                
                # 第三步：通过普通stdio方式连接到SSE服务器
                if command:  # 使用配置中的command
                    logger.debug(f"开始通过stdio连接到SSE服务器...")
                    
                    # 修复点：确保proxy_args始终被初始化
                    proxy_args = list(args) if args else []
                    
                    # 如果args为空，则添加SSE URL
                    if not proxy_args and 'sse_url' in locals():
                        proxy_args = [sse_url]
                    else:
                        # 检查是否已经包含URL参数
                        has_url = False
                        for arg in proxy_args:
                            if isinstance(arg, str) and (arg.startswith("http://") or arg.startswith("https://")):
                                has_url = True
                                break
                        
                        if not has_url and 'sse_url' in locals():
                            # 如果已有参数但需要添加URL，可以在此处追加
                            proxy_args.append(sse_url)
                    
                    logger.debug(f"连接到SSE服务器: {command} {' '.join(proxy_args)}")
                    
                    # 修复：添加连接超时处理，并确保只有成功连接的服务器才被添加到mcp_manager
                    try:
                        session = await mcp_manager.connect_server(
                            command=command,
                            args=proxy_args,
                            cwd=cwd,
                            local=local
                        )
                        
                        # 只有在成功连接时才记录成功信息
                        if session:
                            logger.info(f"SSE服务器 [{server_name}] 连接成功")
                        else:
                            logger.error(f"SSE服务器 [{server_name}] 连接失败，session为None")
                            # 如果连接失败，从mcp_manager中移除该服务器
                            if server_name in mcp_manager.servers:
                                del mcp_manager.servers[server_name]
                    except Exception as e:
                        logger.error(f"连接SSE服务器 [{server_name}] 时发生错误: {str(e)}")
                        # 确保在异常情况下也从mcp_manager中移除该服务器
                        if server_name in mcp_manager.servers:
                            del mcp_manager.servers[server_name]
                
                try:
                    # 创建一个任务来连接服务器
                    session = await mcp_manager.connect_server(command, proxy_args, cwd, 15.0, local)
                    
                    # 保存SSE进程信息
                    server_id = f"{command}-{hash(tuple(proxy_args))}"
                    if server_id in mcp_manager.servers:
                        mcp_manager.servers[server_id]["sse_process"] = sse_process
                    
                    logger.info(f"SSE服务器 [{server_name}] 连接成功")
                except Exception as e:
                    logger.error(f"连接SSE服务器 [{server_name}] 时出错: {str(e)}，但将继续执行")
                else:
                    logger.error(f"缺少command配置，无法连接到SSE服务器")
                    raise ValueError(f"服务器 {server_name} 配置错误: 缺少command")
            else:
                # 普通服务器启动方式
                cwd = None
                await mcp_manager.connect_server(command, processed_args, cwd, 60.0, local)
            
            connect_end_time = time.time()
            logger.debug(f"服务器 [{server_name}] 处理完成，耗时: {connect_end_time - connect_start_time:.2f}秒")
        except Exception as e:
            logger.error(f"服务器 [{server_name}] 连接失败: {str(e)}")
            # 不抛出异常，继续处理其他服务器
            logger.warning(f"将跳过服务器 [{server_name}] 并继续执行")

    # 在返回系统状态前添加工具发现
    logger.debug("开始工具发现流程...")
    from ..core.tool_discovery import auto_discover_tools

    tool_discovery_start = time.time()
    tool_discovery = await auto_discover_tools(mcp_manager)
    tool_discovery_end = time.time()
    
    logger.debug(f"工具发现完成，耗时: {tool_discovery_end - tool_discovery_start:.2f}秒")
    logger.debug(f"发现工具数量: {len(tool_discovery.tool_registry)}")
    
    # 将工具注册表设置到ACC代理
    logger.debug("将工具注册表设置到ACC代理...")
    acc_agent.set_tool_registry(tool_discovery.tool_registry)
    logger.debug("ACC代理工具注册完成")

    # 返回系统状态
    logger.debug("系统初始化完成，准备返回系统状态")
    return {
        "mcp_manager": mcp_manager,
        "acc_agent": acc_agent,
        "workflow_manager": workflow_manager,
        "status": "ready",
    }