# -*- coding: utf-8 -*-

"""命令行交互模块"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def show_welcome_message():
    """显示欢迎信息"""
    print("欢迎使用Auto-Central-Control系统！")
    print("输入 'exit' 或 'quit' 退出系统")


def get_user_input() -> str:
    """获取用户输入，要求连续按三次回车确认发送"""
    print("\n请输入指令 (连续按三次回车确认发送):")
    
    lines = []
    empty_line_count = 0
    
    while True:
        try:
            # 使用内置input函数获取一行输入
            line = input()
            
            # 检查是否为空行
            if line.strip() == "":
                empty_line_count += 1
                # 如果已经有内容并且连续三次空行，则确认发送
                if lines and empty_line_count >= 2:
                    break
            else:
                # 非空行，重置空行计数
                empty_line_count = 0
                lines.append(line)
        except EOFError:
            # 处理EOF（如Ctrl+D）
            break
    
    # 合并所有行，但去掉最后两个空行
    return "\n".join(lines)


# 修改show_response函数，确保它能处理不同格式的响应
def show_response(response: Dict[str, Any]):
    """显示响应结果"""
    logger.debug(f"显示响应: {response}")

    # 确保响应是字典类型
    if not isinstance(response, dict):
        print(f"\n{response}")
        return

    # 处理不同类型的响应
    if "type" in response:
        # 如果响应中有type字段，按type处理
        if response["type"] == "response":
            print(f"\n{response.get('content', '')}")
        elif response["type"] == "tool_call":
            print(f"\n执行工具: {response.get('name', '')}")
            print(f"参数: {response.get('arguments', {})}")
        else:
            print(f"\n{response.get('content', response.get('status', ''))}")
    elif "status" in response:
        # 如果有status字段，显示status
        print(f"\n{response['status']}")
        if "content" in response:
            print(f"{response['content']}")
    else:
        # 其他情况，尝试显示可能的内容字段
        content = response.get("content", response.get("value", str(response)))
        print(f"\n{content}")


def show_error(error: str):
    """显示错误信息"""
    print(f"\n处理请求时出错: {error}")
