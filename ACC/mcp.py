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
                
                callback(decoded_line)
    
        # 同时处理stdout和stderr
        await asyncio.gather(
            read_stream(process.stdout, lambda l: logger.debug(f"[{name}] {l}")),
            read_stream(process.stderr, lambda l: logger.warning(f"[{name}] {l}"))
        )

    async def connect_server(self, command: str, args: list, cwd: Optional[str] = None, timeout: float = 60.0, local: bool = False):
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
