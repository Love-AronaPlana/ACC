# -*- coding: utf-8 -*-
"""
MCP服务器启动脚本
职责：
1. 启动所有MCP服务器
2. 初始化服务器连接
3. 发现并注册工具
4. 保持服务器运行
5. 提供HTTP API供主程序调用工具
"""

import os
import sys
import json
import time
import asyncio
import logging
import datetime
import signal
import atexit
import aiohttp
from aiohttp import web
from typing import Dict, Any, List, Optional
from getpass import getuser

# 添加当前目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志系统
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(
                "logs", f"mcp_server_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            ),
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("MCP_SERVER")

# 导入MCP相关模块
from ACC.mcp import MCPManager
from ACC.core.tool_discovery import ToolDiscovery

# 在导入部分之后，全局变量定义之前添加这两个函数

def get_current_username():
    """获取当前系统用户名"""
    return os.getenv("USERNAME") or os.getenv("USER") or getuser()

def replace_username_in_config(config, username):
    """
    递归替换配置中的 {UserName} 为实际用户名
    
    Args:
        config: 配置字典或列表
        username: 当前用户名
        
    Returns:
        替换后的配置
    """
    if isinstance(config, dict):
        return {k: replace_username_in_config(v, username) for k, v in config.items()}
    elif isinstance(config, list):
        return [replace_username_in_config(item, username) for item in config]
    elif isinstance(config, str):
        return config.replace("{UserName}", username)
    else:
        return config

# 全局变量，用于存储MCP服务器进程
mcp_manager = None
server_processes = {}
tool_registry = {}

# API服务器配置
API_HOST = "127.0.0.1"
API_PORT = 8765

async def wait_for_sse_server(host, port, max_retries=10, retry_interval=1.0):
    """等待SSE服务器启动并验证HTTP端点可用性"""
    import aiohttp
    
    logger.debug(f"等待SSE服务器启动: http://{host}:{port}/sse")
    
    for i in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{host}:{port}/sse", timeout=2.0) as response:
                    if response.status == 200:
                        logger.debug(f"SSE服务器HTTP端点验证成功")
                        return True
        except Exception as e:
            logger.debug(f"SSE服务器HTTP端点验证尝试 {i+1}/{max_retries} 失败: {str(e)}")
        
        await asyncio.sleep(retry_interval)
    
    logger.warning(f"SSE服务器HTTP端点验证失败，已达到最大重试次数")
    return False

async def discover_tools(mcp_manager):
    """发现并注册所有可用工具"""
    global tool_registry
    
    logger.info("开始发现MCP服务器工具...")
    
    # 创建工具发现服务
    discover = ToolDiscovery(mcp_manager.servers)
    
    # 过滤掉标记为not_tool的服务器
    tool_servers = {
        server_id: server_info 
        for server_id, server_info in mcp_manager.servers.items() 
        if not server_info.get("not_tool", False)
    }
    
    logger.debug(f"工具发现将处理 {len(tool_servers)}/{len(mcp_manager.servers)} 个服务器")
    
    # 使用过滤后的服务器列表进行工具发现
    await discover.discover_tools(tool_servers)
    
    # 保存工具注册表
    tool_registry = discover.tool_registry
    
    logger.info(f"工具发现完成，共发现 {len(tool_registry)} 个工具")
    
    return discover

async def initialize_mcp_servers():
    """初始化所有MCP服务器"""
    global mcp_manager
    
    logger.info("开始初始化MCP服务器...")
    
    # 创建MCP管理器
    mcp_manager = MCPManager()
    
    # 加载MCP服务器配置
    config_path = os.path.join("config", "mcp_server.json")
    logger.debug(f"MCP配置文件路径: {os.path.abspath(config_path)}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        mcp_config = json.load(f)
    
    # 获取当前用户名
    current_username = get_current_username()
    logger.debug(f"当前用户名: {current_username}")
    
    # 替换配置中的 {UserName} 为实际用户名
    mcp_config = replace_username_in_config(mcp_config, current_username)
    
    logger.debug(f"MCP配置加载完成，服务器数量: {len(mcp_config['mcpServers'])}")
    
    # 初始化每个服务器
    for server_name, server_config in mcp_config["mcpServers"].items():
        logger.debug(f"开始处理服务器 [{server_name}]...")
        
        # 获取配置参数
        command = server_config.get("command", "")
        args = server_config.get("args", [])
        transport = server_config.get("transport", "stdio")  # 修改这里，默认为"stdio"
        local = server_config.get("local", "").lower() == "true"
        not_tool = server_config.get("not_tool", "").lower() == "true"
        port = server_config.get("port")
        
        # 新增：当有port参数但没有command和args时，自动添加默认值
        if port and not command and transport == "sse":
            command = "mcp-proxy"
            args = [f"127.0.0.1:{port}/sse"]
            logger.info(f"服务器 [{server_name}] 自动添加默认命令: {command} {args}")
            # 更新配置，以便后续处理
            server_config["command"] = command
            server_config["args"] = args
        
        logger.debug(f"服务器 [{server_name}] 是否为本地工具: {local}")
        logger.debug(f"服务器 [{server_name}] 是否为非工具服务器: {not_tool}")
        logger.debug(f"服务器 [{server_name}] 命令: {command}")
        logger.debug(f"服务器 [{server_name}] 参数: {args}")
        logger.debug(f"服务器 [{server_name}] 传输方式: {transport}")
        
        # 路径预处理
        processed_args = [
            os.path.expandvars(arg) if isinstance(arg, str) and "%" in arg else arg
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
            # 对于非工具服务器，使用直接执行命令的方式而不是建立MCP会话
            if not_tool and transport != "sse":
                logger.info(f"服务器 [{server_name}] 被标记为非工具服务器，将直接执行命令而不建立MCP会话")
                
                # 获取可执行文件路径
                exec_path = mcp_manager._get_executable_path(command)
                
                # 设置工作目录
                cwd = None
                if local:
                    cwd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_tools")
                    if not os.path.exists(cwd):
                        logger.warning(f"本地工具目录不存在: {cwd}，将使用默认目录")
                        cwd = None
                
                # 直接启动进程但不建立MCP会话
                process = await asyncio.create_subprocess_exec(
                    exec_path, *processed_args,
                    cwd=cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # 记录进程信息
                server_id = f"{command}-{hash(tuple(processed_args))}"
                mcp_manager.servers[server_id] = {
                    "command": command,
                    "args": processed_args,
                    "session": None,  # 不创建会话
                    "cwd": cwd,
                    "local": local,
                    "not_tool": not_tool,
                    "process": process  # 保存进程对象
                }
                
                # 启动日志记录任务
                asyncio.create_task(mcp_manager._log_async_output(process, server_name))
                
                # 将进程添加到SSE进程列表中以便后续清理
                mcp_manager.sse_processes.append(process)
                
                logger.info(f"非工具服务器 [{server_name}] 已启动 (PID: {process.pid})")
                
            elif transport == "sse":
                # 获取SSE相关配置
                stdio_command = server_config.get("stdio_command")
                stdio_args = server_config.get("stdio_args", [])
                port = server_config.get("port")
                host = "127.0.0.1"
                url = server_config.get("url", "")
                
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
                    cwd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_tools")
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
                
                # 构建SSE URL
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
                        # 启动SSE服务器
                        logger.debug(f"正在启动SSE服务器: {stdio_command} {' '.join(stdio_args)}")
                        sse_process = await mcp_manager.start_sse_server(stdio_command, stdio_args, cwd, local)
                        
                        # 验证服务器是否启动成功
                        server_ready = await wait_for_sse_server(host, port)
                        if not server_ready:
                            logger.warning(f"SSE服务器HTTP端点验证超时，但将继续尝试连接")
                
                # 通过普通stdio方式连接到SSE服务器
                if command:
                    logger.debug(f"开始通过stdio连接到SSE服务器...")
                    
                    # 确保proxy_args始终被初始化
                    proxy_args = list(processed_args) if processed_args else []
                    
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
                        
                        # 修改这里：如果已经有URL参数，不要再添加
                        # 如果没有URL参数但需要添加URL，则清空现有参数并只使用URL
                        if not has_url and 'sse_url' in locals():
                            # 清空现有参数，只使用URL
                            proxy_args = [sse_url]
                    
                    logger.debug(f"连接到SSE服务器: {command} {' '.join(proxy_args)}")
                    
                    # 添加连接超时处理
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
                else:
                    logger.error(f"缺少command配置，无法连接到SSE服务器")
                    raise ValueError(f"服务器 {server_name} 配置错误: 缺少command")
            else:
                # 普通服务器启动方式
                cwd = None
                session = await mcp_manager.connect_server(command, processed_args, cwd, 120.0, local, not_tool)  # 传递not_tool参数
            
            connect_end_time = time.time()
            logger.debug(f"服务器 [{server_name}] 处理完成，耗时: {connect_end_time - connect_start_time:.2f}秒")
        except Exception as e:
            logger.error(f"服务器 [{server_name}] 连接失败: {str(e)}")
            # 不抛出异常，继续处理其他服务器
            logger.warning(f"将跳过服务器 [{server_name}] 并继续执行")
    
    # 发现工具
    logger.debug("开始工具发现流程...")
    tool_discovery_start = time.time()
    await discover_tools(mcp_manager)
    tool_discovery_end = time.time()
    
    logger.debug(f"工具发现完成，耗时: {tool_discovery_end - tool_discovery_start:.2f}秒")
    
    logger.info("MCP服务器初始化完成")
    return mcp_manager

def cleanup():
    """清理资源，关闭所有MCP服务器"""
    logger.info("正在关闭所有MCP服务器...")
    
    if mcp_manager:
        # 创建一个新的事件循环来运行异步关闭函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(mcp_manager.close_all())
        except Exception as e:
            logger.error(f"关闭MCP服务器时出错: {str(e)}")
        finally:
            loop.close()
    
    logger.info("所有MCP服务器已关闭")

def signal_handler(sig, frame):
    """处理终止信号"""
    logger.info(f"接收到终止信号 {sig}，正在关闭...")
    cleanup()
    sys.exit(0)

# API服务器路由处理函数
# 在文件中添加 _convert_to_serializable 函数的定义
# 添加在 handle_call_tool 函数之前

def _convert_to_serializable(obj):
    """递归转换对象为可序列化的格式"""
    if isinstance(obj, dict):
        return {k: _convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_serializable(item) for item in obj]
    elif hasattr(obj, 'text') and isinstance(obj.text, str):
        return obj.text
    elif hasattr(obj, 'result'):  # 处理 CallToolResult 类型
        return _convert_to_serializable(obj.result)
    elif hasattr(obj, '__dict__'):
        return _convert_to_serializable(obj.__dict__)
    elif hasattr(obj, 'to_dict'):
        return obj.to_dict()
    else:
        try:
            # 尝试直接序列化
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            # 如果无法序列化，转为字符串
            return str(obj)

async def handle_call_tool(request):
    """处理工具调用请求"""
    try:
        data = await request.json()
        tool_name = data.get('tool_name')
        tool_args = data.get('tool_args', {})
        
        if not tool_name:
            return web.json_response({"error": "缺少工具名称"}, status=400)
        
        # 确保参数中的Unicode编码被正确处理
        tool_args_str = json.dumps(tool_args, ensure_ascii=False)
        logger.debug(f"API请求: 调用工具 {tool_name} 参数: {tool_args_str}")
        
        # 查找工具
        found_tool = None
        found_tool_info = None
        
        # 1. 首先尝试直接匹配完整工具ID
        if tool_name in tool_registry:
            found_tool = tool_name
            found_tool_info = tool_registry[tool_name]
        else:
            # 2. 尝试查找不带服务器ID前缀的工具名称
            for registry_tool_name, registry_tool_info in tool_registry.items():
                # 检查工具名称是否匹配（忽略服务器ID前缀）
                if registry_tool_name.endswith(f":{tool_name}") or registry_tool_name.split(":")[-1] == tool_name:
                    found_tool = registry_tool_name
                    found_tool_info = registry_tool_info
                    logger.debug(f"找到匹配工具: {found_tool}，原始请求工具名: {tool_name}")
                    break
        
        if not found_tool or not found_tool_info:
            return web.json_response({"error": f"工具 {tool_name} 不存在"}, status=404)
        
        server_id = found_tool_info.get("server")
        
        if not server_id or server_id not in mcp_manager.servers:
            return web.json_response({"error": f"工具 {tool_name} 所属服务器不存在"}, status=404)
        
        # 调用工具
        try:
            # 获取正确的工具名称（可能是服务器内部使用的名称）
            actual_tool_name = found_tool_info.get("name", tool_name.split(":")[-1])
            
            # 获取服务器对象
            server = mcp_manager.servers[server_id]
            
            # 根据服务器对象的类型选择正确的调用方式
            if hasattr(server, "session") and server.session is not None:
                # 如果服务器对象有 session 属性，使用 session 调用工具
                result = await server.session.call_tool(actual_tool_name, tool_args)
            elif hasattr(server, "call_tool") and callable(server.call_tool):
                # 如果服务器对象直接有 call_tool 方法
                result = await server.call_tool(actual_tool_name, tool_args)
            elif isinstance(server, dict) and "session" in server and server["session"] is not None:
                # 如果服务器是字典且有 session 键
                result = await server["session"].call_tool(actual_tool_name, tool_args)
            else:
                # 如果都没有，返回错误
                return web.json_response({"error": f"服务器 {server_id} 不支持工具调用"}, status=500)
                
            logger.debug(f"工具调用成功: {tool_name}")
            
            # 修复：处理特殊类型的结果
            try:
                # 使用 _convert_to_serializable 函数处理结果
                result_dict = _convert_to_serializable(result)
                
                # 尝试直接序列化，确保结果可以被JSON序列化
                json_str = json.dumps(result_dict, ensure_ascii=False)
                result_dict = json.loads(json_str)
            except (TypeError, ValueError) as e:
                logger.warning(f"结果序列化失败: {str(e)}")
                # 如果无法序列化，将结果转为字符串
                result_dict = {"result": str(result)}
            
            return web.json_response(result_dict)
        except Exception as e:
            error_msg = f"工具调用失败: {str(e)}"
            logger.error(error_msg)
            return web.json_response({"error": error_msg}, status=500)
    except Exception as e:
        error_msg = f"处理请求失败: {str(e)}"
        logger.error(error_msg)
        return web.json_response({"error": error_msg}, status=500)
async def handle_tool_registry(request):
    """返回工具注册表"""
    return web.json_response(tool_registry)

async def handle_status(request):
    """返回服务器状态"""
    if not mcp_manager:
        return web.json_response({'status': 'not_initialized'})
    
    active_servers = len(mcp_manager.servers)
    return web.json_response({
        'status': 'running',
        'active_servers': active_servers,
        'tool_count': len(tool_registry)
    })

# 添加新的API端点处理函数
async def handle_server_outputs(request):
    """返回服务器输出信息"""
    if not mcp_manager:
        return web.json_response({'error': 'MCP服务器未初始化'}, status=503)
    
    # 获取查询参数
    server_id = request.query.get('server_id')
    try:
        max_lines = int(request.query.get('max_lines', '100'))
    except ValueError:
        max_lines = 100
    
    # 获取服务器输出
    outputs = mcp_manager.get_server_output(server_id, max_lines)
    
    return web.json_response({
        'outputs': outputs,
        'server_count': len(outputs),
        'timestamp': datetime.datetime.now().isoformat()
    })

async def start_api_server():
    """启动API服务器"""
    app = web.Application()
    
    # 添加路由
    app.router.add_post('/api/call_tool', handle_call_tool)
    app.router.add_get('/api/tool_registry', handle_tool_registry)
    app.router.add_get('/api/status', handle_status)
    app.router.add_get('/api/server_outputs', handle_server_outputs)  # 添加新的路由
    
    # 启动服务器
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, API_HOST, API_PORT)
    
    logger.info(f"启动API服务器: http://{API_HOST}:{API_PORT}")
    await site.start()
    
    return runner

async def keep_alive():
    """保持服务器运行，并定期检查服务器状态"""
    logger.info("MCP服务器已启动并保持运行中...")
    logger.info(f"API服务器地址: http://{API_HOST}:{API_PORT}")
    logger.info("按 Ctrl+C 可以安全关闭所有服务器")
    
    try:
        while True:
            # 每60秒检查一次服务器状态
            await asyncio.sleep(60)
            
            # 检查服务器状态
            if mcp_manager:
                active_servers = len(mcp_manager.servers)
                logger.debug(f"当前活动服务器数量: {active_servers}")
                
                # 如果没有活动服务器，可以选择重新初始化
                if active_servers == 0:
                    logger.warning("没有活动的MCP服务器，考虑重新初始化")
                    # 这里可以添加重新初始化的逻辑
    except asyncio.CancelledError:
        logger.info("保持运行任务被取消")
    except Exception as e:
        logger.error(f"保持运行任务出错: {str(e)}")

async def main():
    """主函数"""
    try:
        # 初始化MCP服务器
        await initialize_mcp_servers()
        
        # 启动API服务器
        api_runner = await start_api_server()
        
        # 保持服务器运行
        await keep_alive()
    except Exception as e:
        logger.error(f"MCP服务器启动失败: {str(e)}")
        return 1
    finally:
        # 确保在退出前关闭所有服务器
        cleanup()
    
    return 0

if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 注册退出处理函数
    atexit.register(cleanup)
    
    # 运行主函数
    sys.exit(asyncio.run(main()))