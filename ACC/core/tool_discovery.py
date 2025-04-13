# -*- coding: utf-8 -*-

import logging
from typing import Dict, Any
from mcp import ClientSession

logger = logging.getLogger(__name__)


class ToolDiscovery:
    """工具发现服务，用于获取并展示所有MCP服务器工具"""

    def __init__(self, mcp_servers: Dict[str, Any]):
        """
        Args:
            mcp_servers: MCP服务器字典，来自MCPManager的servers属性
        """
        self.servers = mcp_servers
        self.tool_registry = {}

    async def discover_tools(self, servers=None):
        """发现并注册所有可用工具
        
        Args:
            servers: 可选的服务器字典，如果提供则使用此字典而非self.servers
        """
        logger.info("开始发现MCP服务器工具...")
        
        # 使用提供的服务器列表或默认的self.servers
        target_servers = servers if servers is not None else self.servers

        for server_id, server_info in target_servers.items():
            # 跳过标记为not_tool的服务器
            if server_info.get("not_tool", False):
                logger.debug(f"跳过非工具服务器: {server_id}")
                continue
                
            session = server_info.get("session")
            if not session:
                logger.warning(f"服务器 {server_id} 没有有效会话，跳过工具发现")
                continue
                
            try:
                response = await session.list_tools()
                self._process_tools(server_id, response.tools)
            except Exception as e:
                logger.error(f"从服务器 {server_id} 获取工具失败: {str(e)}")

        self._display_discovered_tools()

    def _process_tools(self, server_id: str, tools: list):
        """处理从MCP服务器获取的工具信息

        Args:
            server_id: MCP服务器唯一标识符，格式示例: "npx-2926528640140537"
            tools: 从MCP服务器获取的工具列表，每个工具包含以下属性:
                - name: 工具名称（如 "read_file"）
                - description: 工具描述（如 "Read the complete contents of a file..."）
                - inputSchema: 输入参数JSON Schema（如 {'type': 'object', ...}）

        处理逻辑:
            1. 生成工具唯一标识符: server_id + tool.name
            2. 检查工具是否已注册，避免重复
            3. 将工具元数据存入注册表，包含以下信息:
               - server: 所属服务器ID
               - name: 工具名称
               - description: 功能描述
               - input_schema: 输入参数规范
        """
        for tool in tools:
            tool_key = f"{server_id}:{tool.name}"

            if tool_key in self.tool_registry:
                logger.warning(f"发现重复工具: [{server_id}] {tool.name}，已跳过")
                continue

            # 新增调试日志（记录工具元数据的关键信息）
            logger.debug(
                f"注册工具: {tool_key}\n"
                f"描述摘要: {tool.description[:40]}...\n"
                f"输入参数示例: {str(tool.inputSchema)[:50]}..."
            )
            
            # 不在这里替换描述，而是保存原始描述
            self.tool_registry[tool_key] = {
                "server": server_id,
                "name": tool.name,
                "tool_name": f"{server_id}:{tool.name}",
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }

    def _display_discovered_tools(self):
        """显示已发现的工具信息"""
        if not self.tool_registry:
            logger.warning("未发现任何可用工具")
            return

        logger.info("发现 %d 个可用工具:\n", len(self.tool_registry))
        for i, (tool_key, tool_info) in enumerate(self.tool_registry.items(), 1):
            logger.info(
                f"{i}. [{tool_info['server']}] {tool_info['name']}\n"
                f"   描述: {tool_info['description']}\n"
                f"   输入参数: {tool_info['input_schema']}\n"
                "----------------------------------------"
            )


async def auto_discover_tools(mcp_manager) -> ToolDiscovery:
    """自动工具发现入口函数"""
    discover = ToolDiscovery(mcp_manager.servers)
    await discover.discover_tools()
    return discover
