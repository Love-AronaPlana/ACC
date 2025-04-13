# -*- coding: utf-8 -*-

"""
工具调用模块

该模块负责与MCP服务器提供的工具通信
"""

import json
import logging
import sys
import aiohttp
import asyncio  # 添加这一行导入
import os
from typing import Dict, Any, Optional, Tuple
from ..agent import get_acc_agent
# 移除不存在的导入
# from ..prompt.system import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# 添加全局变量来跟踪免确认次数
_skip_confirmation_count = 0

# 添加MCP API客户端类
class MCPAPIClient:
    """MCP API客户端，用于与独立运行的MCP服务器通信"""
    
    def __init__(self):
        """初始化MCP API客户端"""
        self.base_url = None
        self.initialized = False
        self.logger = logging.getLogger("ACC.function.use_tool")  # 添加logger属性
        self._init_from_file()
    
    # 修改 MCPAPIClient 类的 _init_from_file 方法
    def _init_from_file(self):
        """从配置文件初始化API客户端"""
        try:
            # 首先尝试从config.toml加载配置
            from ..config import get_config
            config = get_config()
            mcp_config = config.get("mcp", {})
            
            # 检查配置中是否有MCP服务器地址
            if "api_url" in mcp_config:
                self.base_url = mcp_config["api_url"]
                logger.info(f"从config.toml加载MCP服务器API地址: {self.base_url}")
                self.initialized = True
                return
            
            # 如果配置中没有，使用默认地址
            self.base_url = "http://127.0.0.1:8765/api"
            logger.info(f"使用默认MCP服务器API地址: {self.base_url}")
            self.initialized = True
        except Exception as e:
            logger.error(f"初始化MCP API客户端失败: {str(e)}")
            self.initialized = False
    
    # 添加 check_status 方法
    async def check_status(self) -> Dict[str, Any]:
        """检查MCP服务器状态"""
        if not self.initialized:
            self._init_from_file()
            
        if not self.base_url:
            return {"success": False, "error": "MCP服务器API地址未初始化"}
        
        url = f"{self.base_url}/status"
        
        logger.debug(f"检查MCP服务器状态: {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=2.0) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        return {"success": True, "status": response_data}
                    else:
                        return {"success": False, "error": f"HTTP错误: {response.status}"}
        except Exception as e:
            logger.debug(f"MCP服务器连接失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # 确保 MCPAPIClient 类的 call_tool 方法正确处理错误
    
    async def call_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        if not self.initialized:
            self._init_from_file()
            
        if not self.base_url:
            raise ValueError("MCP服务器API地址未初始化")
        
        url = f"{self.base_url}/call_tool"
        payload = {
            "tool_name": tool_name,
            "tool_args": tool_args
        }
        
        # 添加重试逻辑
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result
                        else:
                            error_text = await response.text()
                            try:
                                error_data = json.loads(error_text) if error_text else {"error": f"HTTP错误: {response.status}"}
                                error_msg = error_data.get("error", f"HTTP错误: {response.status}")
                            except json.JSONDecodeError:
                                error_msg = f"HTTP错误: {response.status}, 响应: {error_text}"
                            
                            # 如果是服务器不支持工具调用的错误，尝试重试
                            if "不支持工具调用" in error_msg and retry_count < max_retries:
                                self.logger.warning(f"工具调用异常，尝试重试 ({retry_count+1}/{max_retries}): {error_msg}")
                                retry_count += 1
                                await asyncio.sleep(1)  # 等待1秒后重试
                                continue
                            
                            raise ValueError(f"工具调用失败: {error_msg}")
            except json.JSONDecodeError:
                if retry_count < max_retries:
                    self.logger.warning(f"JSON解析错误，尝试重试 ({retry_count+1}/{max_retries})")
                    retry_count += 1
                    await asyncio.sleep(1)
                    continue
                raise ValueError("工具调用失败: 无法解析响应")
            except Exception as e:
                if retry_count < max_retries:
                    self.logger.warning(f"工具调用异常，尝试重试 ({retry_count+1}/{max_retries}): {str(e)}")
                    retry_count += 1
                    await asyncio.sleep(1)
                    continue
                raise ValueError(f"工具调用失败: {str(e)}")
        logger.debug(f"发送工具调用请求到MCP服务器: {url}")
        logger.debug(f"请求参数: {payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    error_msg = response_data.get('error', f"HTTP错误: {response.status}")
                    logger.error(f"工具调用失败: {error_msg}")
                    raise ValueError(f"工具调用失败: {error_msg}")
                
                if not response_data.get('success', False):
                    error_msg = response_data.get('error', "未知错误")
                    logger.error(f"工具调用失败: {error_msg}")
                    raise ValueError(f"工具调用失败: {error_msg}")
                
                result = response_data.get('result')
                logger.debug(f"工具调用成功，结果: {result}")
                return result
    
    async def get_tool_registry(self) -> Dict[str, Any]:
        """获取工具注册表"""
        if not self.initialized:
            self._init_from_file()
            
        if not self.base_url:
            raise ValueError("MCP服务器API地址未初始化")
        
        url = f"{self.base_url}/tool_registry"
        
        logger.debug(f"获取工具注册表: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    error_msg = f"获取工具注册表失败: HTTP错误 {response.status}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                response_data = await response.json()
                return response_data

# 创建全局MCP API客户端实例
_mcp_api_client = None

def get_mcp_api_client() -> MCPAPIClient:
    """获取MCP API客户端实例"""
    global _mcp_api_client
    if _mcp_api_client is None:
        _mcp_api_client = MCPAPIClient()
    return _mcp_api_client

def _get_direct_input(prompt: str) -> str:
    """
    直接从标准输入获取用户输入，不使用任何其他输入函数
    要求用户连续按三次回车才能确认发送
    
    Args:
        prompt: 提示用户的文本
        
    Returns:
        用户输入的字符串
    """
    # 直接使用sys.stdout和sys.stdin，避免使用input()函数
    sys.stdout.write(prompt)
    sys.stdout.write("\n(请连续按三次回车确认发送)\n")
    sys.stdout.flush()
    
    lines = []
    empty_line_count = 0
    
    while True:
        line = sys.stdin.readline()
        
        # 检查是否为空行（只有换行符）
        if line.strip() == "":
            empty_line_count += 1
            # 如果已经有内容并且连续三次空行，则确认发送
            if lines and empty_line_count >= 2:
                break
        else:
            # 非空行，重置空行计数
            empty_line_count = 0
            lines.append(line)
    
    # 合并所有行，但去掉最后两个空行
    return "".join(lines).rstrip()

def get_tool_confirmation(tool_name: str, formatted_args: str) -> Tuple[bool, int, Optional[str]]:
    """
    获取用户对工具调用的确认，完全独立于主交互循环
    
    Args:
        tool_name: 工具名称
        formatted_args: 格式化后的工具参数
        
    Returns:
        tuple: (是否确认执行, 免确认次数, 用户输入的消息)
        如果用户输入了非预期内容，则返回(None, 0, 用户输入)
    """
    # 使用明显的分隔符，确保用户注意到这是工具确认
    sys.stdout.write("\n" + "="*60 + "\n")
    sys.stdout.write(f"【工具操作确认】准备执行工具: {tool_name}\n")
    sys.stdout.write(f"【工具参数】:\n{formatted_args}\n")
    sys.stdout.write("="*60 + "\n\n")
    sys.stdout.write("请选择操作:\n")
    sys.stdout.write("  y - 确认执行此工具\n")
    sys.stdout.write("  n - 拒绝执行此工具\n")
    sys.stdout.write("  数字 - 设置接下来免确认的次数\n")
    sys.stdout.write("  其他内容 - 取消工具调用，将输入内容发送给AI\n")
    sys.stdout.flush()
    
    try:
        # 使用自定义的输入函数，避免与主交互循环混淆
        user_input = _get_direct_input("\n【工具确认】请输入您的选择: ")
        
        if user_input.lower() == 'y':
            sys.stdout.write("已确认执行工具操作\n")
            sys.stdout.flush()
            return True, 0, None
        elif user_input.lower() == 'n':
            sys.stdout.write("已拒绝执行工具操作\n")
            sys.stdout.flush()
            return False, 0, None
        elif user_input.isdigit():
            skip_count = int(user_input)
            sys.stdout.write(f"已设置接下来 {skip_count} 次工具调用免确认\n")
            sys.stdout.flush()
            return True, skip_count, None
        else:
            # 用户输入了其他内容，将作为消息发送给AI
            sys.stdout.write("已取消工具调用，将您的输入发送给AI处理\n")
            sys.stdout.flush()
            return None, 0, user_input
    except Exception as e:
        logger.error(f"获取用户确认时出错: {str(e)}")
        sys.stdout.write("输入处理出错，请重新输入\n")
        sys.stdout.flush()
        return False, 0, None

async def call_tool(tool_name: str, tool_args: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    调用指定的工具
    
    Args:
        tool_name: 工具名称
        tool_args: 工具参数，默认为None，会被转换为空字典
        
    Returns:
        工具调用结果
    """
    global _skip_confirmation_count
    
    # 确保tool_args是字典类型
    if tool_args is None:
        tool_args = {}
        
    logger.debug(f"开始调用工具 - 工具名称: {tool_name}, 参数: {json.dumps(tool_args, ensure_ascii=False)}")
    
    # 获取ACC代理和工具注册表
    agent = get_acc_agent()
    tool_registry = agent.tool_registry
    
    # 查找工具
    found_tool = None
    server_id = None
    for tool_key, tool_info in tool_registry.items():
        if tool_info["name"] == tool_name:
            found_tool = tool_info
            # 从工具键中提取服务器ID (格式: server_id:tool_name)
            server_id = tool_key.split(":")[0] if ":" in tool_key else None
            break
    
    # 如果没有找到工具，返回错误信息
    if not found_tool:
        error_msg = f"工具 {tool_name} 不存在"
        logger.warning(f"工具未找到 - 请求名称: {tool_name}")
        return {"error": error_msg}
    
    # 添加用户确认逻辑
    if _skip_confirmation_count <= 0:
        # 格式化工具参数以便显示
        formatted_args = json.dumps(tool_args, ensure_ascii=False, indent=2)
        
        # 使用专用的确认函数获取用户确认
        confirmed, skip_count, user_message = get_tool_confirmation(tool_name, formatted_args)
        
        # 如果用户输入了非预期内容，将其发送给AI
        if confirmed is None and user_message:
            logger.info(f"用户取消工具调用，发送消息: {user_message}")
            # 将用户消息发送给AI，使用已导入的get_acc_agent
            acc_agent = get_acc_agent()
            response = acc_agent.process_request(user_message, user_status="user_message")
            return {
                "type": "user_message",
                "message": user_message,
                "ai_response": response,
                "skip_tool": True
            }
        
        # 更新免确认次数
        _skip_confirmation_count = skip_count
        
        # 如果用户拒绝执行，返回错误信息
        if not confirmed:
            logger.info(f"用户拒绝执行工具: {tool_name}")
            return {"error": f"用户拒绝执行工具: {tool_name}"}
        
        logger.info(f"用户确认执行工具: {tool_name}")
    else:
        # 减少免确认次数
        _skip_confirmation_count -= 1
        logger.info(f"免确认执行工具: {tool_name}，剩余免确认次数: {_skip_confirmation_count}")
        # 显示免确认执行信息
        sys.stdout.write(f"\n【自动执行】工具 {tool_name} (剩余免确认次数: {_skip_confirmation_count})\n")
        sys.stdout.flush()
    
    try:
        # 使用MCP API客户端调用工具
        mcp_client = get_mcp_api_client()
        logger.debug(f"执行工具调用 - 工具: {tool_name}, 参数: {json.dumps(tool_args, ensure_ascii=False)}")
        result = await mcp_client.call_tool(tool_name, tool_args)
        
        # 处理结果
        logger.debug(f"工具调用成功 - 结果: {result}")
        return {
            "success": True,
            "tool_name": tool_name,
            "result": result,
            "raw_result": result
        }
    except Exception as e:
        error_msg = f"工具调用失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}


def format_tool_result(result: Dict[str, Any]) -> str:
    """
    格式化工具调用结果为可读字符串
    
    Args:
        result: 工具调用结果
        
    Returns:
        格式化后的结果字符串
    """
    # 检查是否是用户消息
    if result.get("type") == "user_message" and result.get("skip_tool"):
        # 这是用户输入的消息，已经发送给AI
        ai_response = result.get("ai_response", {})
        if "content" in ai_response:
            return f"Here is what you requested:\n{ai_response['content']}"
        elif "status" in ai_response:
            return f"Here is what you requested::\n{ai_response['status']}"
        else:
            return f"已将您的消息发送给AI"
    
    if "error" in result:
        return f"工具调用失败: {result['error']}"
    
    if result.get("success"):
        tool_name = result.get("tool_name", "未知工具")
        tool_result = result.get("result", {})
        
        # 尝试将结果格式化为JSON字符串
        try:
            if isinstance(tool_result, dict) or isinstance(tool_result, list):
                formatted_result = json.dumps(tool_result, ensure_ascii=False, indent=2)
            else:
                formatted_result = str(tool_result)
        except Exception:
            formatted_result = str(tool_result)
        
        return f"工具 {tool_name} 调用成功:\n{formatted_result}"
    
    return "工具调用结果格式错误"