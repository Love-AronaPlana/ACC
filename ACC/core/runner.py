# -*- coding: utf-8 -*-

"""主运行循环模块"""

import logging
import json
import traceback  # 添加traceback模块用于详细错误信息
from typing import Dict, Any
from ACC.interaction.cli import get_user_input, show_response, show_error
from ACC.function.search_tool_info import get_tool_details
from ACC.function.print_for_user import handle_print_for_user  # 导入新的处理函数
from ACC.function.get_user_input import (
    get_user_input as process_user_input,
)
from ACC.function.use_tool import call_tool, format_tool_result  # 导入工具调用函数

logger = logging.getLogger(__name__)


async def run_main_loop(acc_agent):
    """运行主交互循环"""
    while True:
        try:
            user_input = get_user_input()

            if user_input.lower() in ["exit", "quit"]:
                print("感谢使用，再见！")
                return 0

            # 初始处理用户输入，使用默认的user_message状态
            response = acc_agent.process_request(user_input)

            # 修改这里：确保所有响应都经过统一的处理流程
            # 不再直接显示响应，而是始终进入功能处理流程
            await process_response(response)

        except Exception as e:
            error_msg = f"处理请求时发生错误: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            show_error(error_msg)


async def process_response(response: Dict[str, Any]):
    """处理LLM响应"""
    try:
        # 获取功能名称和值
        function_name = response.get("function", "")
        function_value = response.get("value", "")
        tool_value = response.get("tool_value")

        # 记录处理信息
        logger.debug(
            f"处理功能: {function_name}, 值: {function_value}, 工具值: {tool_value}"
        )

        # 根据功能名称处理不同的功能
        if function_name == "search_tool_info":
            # 获取工具详情 - 移除 await 关键字，因为 get_tool_details 不是异步函数
            tool_info = get_tool_details(function_value)
            # 显示工具详情
            show_response(tool_info)

            # 修改：将工具信息发送给LLM继续处理，使用process_request而不是不存在的process_tool_result
            from ..agent import get_acc_agent

            acc_agent = get_acc_agent()
            formatted_result = f"工具信息: {json.dumps(tool_info, ensure_ascii=False)}"
            # 使用process_request方法，并指定user_status为tool_result
            response = acc_agent.process_request(
                formatted_result, user_status="tool_info"
            )
            # 递归处理响应
            await process_response(response)

        elif function_name == "print_for_user":
            # 修改：使用print_for_user而不是handle_print_for_user，避免重复请求用户输入
            from ACC.function.print_for_user import print_for_user
            print_for_user(function_value)
            # 不需要继续处理，等待主循环获取下一个用户输入

        elif function_name == "need_user_input":
            # 获取用户输入
            user_input_result = process_user_input(function_value)
            # 处理用户输入结果
            from ..agent import get_acc_agent

            acc_agent = get_acc_agent()
            response = acc_agent.process_request(
                user_input_result["content"],
                user_status=user_input_result.get("user_status", "user_re_message"),
            )
            # 递归处理响应
            await process_response(response)

        elif function_name == "use_tool":
            # 调用工具
            if tool_value is not None:  # 使用 is not None 而不是 if tool_value
                # 根据tool_value的类型进行处理
                if isinstance(tool_value, dict):
                    # 已经是字典类型，直接使用
                    tool_args = tool_value
                elif isinstance(tool_value, str):
                    # 字符串类型，尝试解析为JSON
                    try:
                        # 只有当字符串看起来像JSON时才尝试解析
                        if tool_value.strip().startswith('{') or tool_value.strip().startswith('['):
                            tool_args = json.loads(tool_value)
                        else:
                            # 普通字符串，创建一个包含该字符串的字典
                            tool_args = {"path": tool_value}
                    except json.JSONDecodeError:
                        # JSON解析失败，创建一个包含该字符串的字典
                        logger.warning(f"无法解析tool_value为JSON: {tool_value}")
                        tool_args = {"path": tool_value}
                else:
                    # 其他类型，转换为字符串
                    tool_args = {"value": str(tool_value)}
                
                logger.debug(f"处理后的工具参数: {tool_args}")
                tool_result = await call_tool(function_value, tool_args)
                # 格式化工具结果
                formatted_result = format_tool_result(tool_result)
                # 处理工具调用结果，使用process_request而不是不存在的process_tool_result
                from ..agent import get_acc_agent

                acc_agent = get_acc_agent()
                response = acc_agent.process_request(
                    formatted_result, user_status="tool_message"
                )
                # 递归处理响应
                await process_response(response)
            else:
                # 修改：对于没有参数的工具，传递空字典作为参数
                tool_result = await call_tool(function_value, {})
                # 格式化工具结果
                formatted_result = format_tool_result(tool_result)
                # 处理工具调用结果
                from ..agent import get_acc_agent

                acc_agent = get_acc_agent()
                response = acc_agent.process_request(
                    formatted_result, user_status="tool_message"
                )
                # 递归处理响应
                await process_response(response)

        elif function_name == "tool_list":
            # 获取工具列表
            from ..agent import get_acc_agent

            acc_agent = get_acc_agent()
            tools_list = acc_agent.get_formatted_tools_list()
            # 显示工具列表
            show_response(tools_list)

            # 修改：将工具列表发送给LLM继续处理，使用process_request而不是不存在的process_tool_result
            formatted_result = f"可用工具列表: {tools_list}"
            response = acc_agent.process_request(
                formatted_result, user_status="tool_result"
            )
            # 递归处理响应
            await process_response(response)

        else:
            # 直接显示响应
            show_response(response)
    except Exception as e:
        error_msg = f"处理响应时发生错误: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        show_error(error_msg)
