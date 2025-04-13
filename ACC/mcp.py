# -*- coding: utf-8 -*-

"""MCP服务器管理模块"""

import asyncio
from typing import Dict, Any, Optional, List
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import os
import logging
import shutil
import subprocess
from io import TextIOWrapper

logger = logging.getLogger(__name__)


from .config import get_config


class MCPManager:
    """管理MCP服务器连接"""

    def __init__(self):
        self.servers: Dict[str, Any] = {}
        self.exit_stack = AsyncExitStack()
        self.executable_config = get_config().get("executables", {})
        self.sse_processes = []  # 存储SSE服务器进程
        self.server_outputs = {}  # 存储服务器输出信息

    def _get_executable_path(self, command: str) -> str:
        """获取跨平台可执行文件路径"""
        platform_key = "windows" if os.name == "nt" else "linux"
        platform_config = self.executable_config.get(platform_key, {})

        # 优先使用配置文件中的路径
        if command in platform_config:
            custom_path = platform_config[command]
            if os.path.exists(custom_path):
                return custom_path
            logger.warning(f"配置路径 {custom_path} 不存在，尝试系统查找")

        # 配置不存在时回退到系统查找
        sys_path = shutil.which(command)
        if sys_path:
            return sys_path

        raise FileNotFoundError(f"无法找到 {command} 执行路径")

    async def start_sse_server(self, command: str, args: List[str], cwd: Optional[str] = None, local: bool = False):
        """非阻塞启动SSE服务器进程"""
        exec_path = self._get_executable_path(command)
        
        # 注意：如果已经提供了cwd，则优先使用提供的cwd（SSE服务器路径）
        # 只有在cwd为None且local为True时，才使用local_tools目录
        if cwd is None and local:
            logger.debug(f"使用本地工具目录运行SSE服务器: {command}")
            # 不修改exec_path，因为我们仍然需要系统命令，但会修改工作目录
            cwd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_tools")
            logger.debug(f"设置本地工具工作目录: {cwd}")
        
        logger.debug(f"异步启动SSE服务器: {exec_path} {' '.join(args)}")
    
        # 使用异步子进程创建
        process = await asyncio.create_subprocess_exec(
            exec_path, *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # 启动日志记录任务但不等待完成
        asyncio.create_task(self._log_async_output(process, command))
        
        self.sse_processes.append(process)
        return process

    async def _log_async_output(self, process: asyncio.subprocess.Process, name: str):
        """异步处理进程输出"""
        # 确保服务器输出字典中有该服务器的条目
        if name not in self.server_outputs:
            self.server_outputs[name] = []
        
        async def read_stream(stream, callback):
            while True:
                line = await stream.readline()
                if not line:
                    break
                try:
                    # 首先尝试使用 UTF-8 解码
                    decoded_line = line.decode('utf-8').strip()
                except UnicodeDecodeError:
                    try:
                        # 如果 UTF-8 解码失败，尝试使用系统默认编码（Windows 上通常是 GBK/CP936）
                        if os.name == 'nt':
                            decoded_line = line.decode('gbk', errors='replace').strip()
                        else:
                            # 对于其他系统，使用 'replace' 错误处理策略
                            decoded_line = line.decode('utf-8', errors='replace').strip()
                    except Exception as e:
                        # 如果所有解码方法都失败，记录原始字节并继续
                        logger.warning(f"无法解码输出: {str(e)}, 原始数据: {line}")
                        decoded_line = f"[无法解码的数据: {line!r}]"
                
                # 保存输出到服务器输出字典
                timestamp = asyncio.get_event_loop().time()
                self.server_outputs[name].append({
                    "timestamp": timestamp,
                    "text": decoded_line,
                    "type": "stdout" if stream == process.stdout else "stderr"
                })
                
                # 限制每个服务器存储的输出行数
                if len(self.server_outputs[name]) > 1000:  # 保留最新的1000行
                    self.server_outputs[name] = self.server_outputs[name][-1000:]
                
                callback(decoded_line)
        
        # 同时处理stdout和stderr
        await asyncio.gather(
            read_stream(process.stdout, lambda l: logger.debug(f"[{name}] {l}")),
            read_stream(process.stderr, lambda l: logger.warning(f"[{name}] {l}"))
        )

    # 添加获取服务器输出的方法
    def get_server_output(self, server_id=None, max_lines=100):
        """
        获取指定服务器或所有服务器的输出
        
        Args:
            server_id: 服务器ID，如果为None则返回所有服务器的输出
            max_lines: 每个服务器返回的最大行数
            
        Returns:
            Dict[str, List[str]]: 服务器ID到输出行的映射
        """
        if server_id:
            if server_id in self.server_outputs:
                # 返回指定服务器的最新输出
                outputs = self.server_outputs[server_id][-max_lines:]
                return {server_id: [item["text"] for item in outputs]}
            return {server_id: []}
        
        # 返回所有服务器的输出
        result = {}
        for sid, outputs in self.server_outputs.items():
            result[sid] = [item["text"] for item in outputs[-max_lines:]]
        return result

    async def connect_server(self, command: str, args: list, cwd: Optional[str] = None, timeout: float = 120.0, local: bool = False, not_tool: bool = False):
        # 使用新的路径获取方法
        exec_path = self._get_executable_path(command)
    
        # 注意：如果已经提供了cwd，则优先使用提供的cwd（SSE服务器路径）
        # 只有在cwd为None且local为True时，才使用local_tools目录
        if cwd is None and local:
            logger.debug(f"使用本地工具目录运行: {command}")
            # 修正路径：使用ACC/local_tools
            cwd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_tools")
            logger.debug(f"设置本地工具工作目录: {cwd}")
    
        logger.debug(f"最终使用的执行路径: {exec_path}")
        server_params = StdioServerParameters(
            command=exec_path, args=args, env=None, cwd=cwd  # 添加工作目录参数
        )
    
        try:
            # 添加超时处理
            connect_task = asyncio.create_task(self._connect_with_timeout(server_params, command, args, cwd, timeout))
            
            # 等待连接任务完成，但设置超时
            session = await asyncio.wait_for(connect_task, timeout)
            
            # 使用服务器名称作为ID替代session.id
            server_id = f"{command}-{hash(tuple(args))}"
            logger.info(f"MCP服务器连接成功 [服务器ID: {server_id}]")
    
            self.servers[server_id] = {
                "command": command,
                "args": args,
                "session": session,
                "cwd": cwd,  # 保存工作目录信息
                "local": local,  # 保存是否为本地工具
                "not_tool": not_tool,  # 保存是否为非工具服务器
            }
            return session
    
        except asyncio.TimeoutError:
            logger.warning(f"连接服务器超时: {command} {args}，但将继续执行")
            # 即使超时也创建一个占位会话记录
            server_id = f"{command}-{hash(tuple(args))}"
            self.servers[server_id] = {
                "command": command,
                "args": args,
                "session": None,  # 会话为空
                "cwd": cwd,
                "connection_pending": True,  # 标记连接仍在进行中
                "local": local,  # 保存是否为本地工具
                "not_tool": not_tool,  # 保存是否为非工具服务器
            }
            # 返回None，调用方需要处理这种情况
            return None
        except FileNotFoundError as e:
            logger.error(f"关键依赖缺失: {str(e)}")
            raise

    async def _connect_with_timeout(self, server_params, command, args, cwd, timeout):
        """尝试在指定超时时间内连接到服务器"""
        try:
            # 创建连接
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            logger.debug("成功创建stdio传输管道")
    
            stdio, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
    
            logger.debug("正在初始化MCP会话...")
            # 设置初始化超时
            init_task = asyncio.create_task(session.initialize())
            await asyncio.wait_for(init_task, timeout)  # 使用一半的超时时间用于初始化
            
            return session
        except Exception as e:
            logger.error(f"连接服务器失败: {command} {' '.join(args)}, 错误: {str(e)}")
            raise

    async def close_all(self):
        """清理所有后台任务"""
        logger.info("正在终止SSE后台任务...")
        for server in self.servers.values():
            for task in server.get("tasks", []):
                if not task.done():
                    task.cancel()
        logger.info("正在关闭所有MCP服务器连接...")
        
        # 关闭所有SSE进程
        for process in self.sse_processes:
            if process.poll() is None:  # 如果进程仍在运行
                logger.debug(f"正在终止SSE服务器进程 (PID: {process.pid})")
                try:
                    process.terminate()
                    # 等待进程结束，最多等待5秒
                    for _ in range(50):
                        if process.poll() is not None:
                            break
                        await asyncio.sleep(0.1)
                    
                    # 如果进程仍未结束，强制终止
                    if process.poll() is None:
                        logger.warning(f"SSE服务器进程未响应终止信号，强制终止 (PID: {process.pid})")
                        process.kill()
                except Exception as e:
                    logger.error(f"终止SSE服务器进程时出错: {str(e)}")
        
        # 清空进程列表
        self.sse_processes.clear()
        
        # 关闭所有MCP会话
        await self.exit_stack.aclose()
        self.servers.clear()
        logger.info("所有MCP服务器连接已关闭")


# 在 MCPManager 类中添加以下方法

async def reinitialize_server(self, server_id: str) -> bool:
    """
    尝试重新初始化指定的MCP服务器
    
    Args:
        server_id: 服务器ID
        
    Returns:
        bool: 重新初始化是否成功
    """
    if server_id not in self.servers:
        logger.error(f"服务器 {server_id} 不存在，无法重新初始化")
        return False
        
    # 获取服务器配置
    server_config = None
    for server_name, config in self.config.items():
        if server_name in self.server_id_map and self.server_id_map[server_name] == server_id:
            server_config = config
            server_name_key = server_name
            break
    
    if not server_config:
        logger.error(f"找不到服务器 {server_id} 的配置信息，无法重新初始化")
        return False
    
    # 关闭现有连接
    try:
        server = self.servers[server_id]
        if hasattr(server, "close") and callable(server.close):
            await server.close()
        elif hasattr(server, "session") and hasattr(server.session, "close") and callable(server.session.close):
            await server.session.close()
    except Exception as e:
        logger.warning(f"关闭服务器 {server_id} 连接时出错: {str(e)}")
    
    # 重新初始化连接
    try:
        # 使用与初始化相同的逻辑
        is_local_tool = server_config.get("is_local_tool", False)
        
        if is_local_tool:
            # 本地工具处理
            module_path = server_config.get("module_path", "")
            if not module_path:
                logger.error(f"本地工具 {server_name_key} 缺少module_path配置")
                return False
                
            try:
                module = importlib.import_module(module_path)
                self.servers[server_id] = module
                logger.info(f"本地工具 {server_name_key} 加载成功")
                return True
            except Exception as e:
                logger.error(f"加载本地工具 {server_name_key} 失败: {str(e)}")
                return False
        else:
            # 外部MCP服务器处理
            command = server_config.get("command", "")
            args = server_config.get("args", [])
            transport = server_config.get("transport", "")
            
            if not command:
                logger.error(f"服务器 {server_name_key} 缺少command配置")
                return False
                
            # 验证文件系统路径
            if server_name_key == "filesystem" and args:
                paths = []
                for arg in args:
                    if os.path.isdir(arg):
                        paths.append(arg)
                
                if paths:
                    logger.debug(f"验证文件系统路径: {paths}")
                    for path in paths:
                        if os.path.isdir(path):
                            logger.debug(f"路径验证通过: {path}")
                        else:
                            logger.warning(f"路径验证失败: {path}")
            
            logger.debug(f"开始连接服务器 {server_name_key}...")
            
            # 查找命令的完整路径
            cmd_path = await find_executable(command)
            if not cmd_path:
                logger.error(f"找不到命令: {command}")
                return False
                
            logger.debug(f"最终使用的执行路径: {cmd_path}")
            
            # 创建stdio传输
            try:
                transport_params = StdioServerParameters(
                    command=cmd_path,
                    args=args
                )
                
                # 创建stdio传输
                transport = await stdio_client(transport_params)
                logger.debug(f"成功创建stdio传输管道")
                
                # 初始化MCP会话
                logger.debug(f"正在初始化MCP会话...")
                session = ClientSession(transport)
                
                # 等待连接成功
                await session.wait_for_ready()
                
                # 保存会话
                self.servers[server_id] = session
                logger.info(f"MCP服务器连接成功 [服务器ID: {server_id}]")
                return True
            except Exception as e:
                logger.error(f"连接服务器 {server_name_key} 失败: {str(e)}")
                return False
    except Exception as e:
        logger.error(f"重新初始化服务器 {server_id} 失败: {str(e)}")
        return False
