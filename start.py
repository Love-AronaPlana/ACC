# -*- coding: utf-8 -*-
"""系统启动入口：主程序启动脚本，包含日志配置和异步事件循环初始化"""

import sys
import logging
import os
import asyncio
import datetime
from ACC.interaction.cli import show_welcome_message
from ACC.system.initializer import initialize
from ACC.core.runner import run_main_loop

# 配置全局日志系统
# DEBUG级别记录所有日志，同时输出到文件和控制台
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # 包含时间、模块名、日志级别和消息
    handlers=[
        logging.FileHandler(  # 文件处理器
            os.path.join(
                "logs", f"acc_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            ),
            encoding="utf-8",  # 明确指定编码为UTF-8（防止中文乱码）
        ),
        logging.StreamHandler(),  # 控制台处理器
    ],
)

# 确保日志目录存在（自动创建logs文件夹）
os.makedirs("logs", exist_ok=True)


async def async_main():
    """异步主入口函数
    职责：
    1. 初始化系统组件
    2. 显示欢迎信息
    3. 运行主事件循环
    4. 异常处理和资源清理
    """
    system_state = None
    try:
        # 初始化系统核心组件（ACC代理、MCP管理器等）
        system_state = await initialize()
        # 显示命令行欢迎界面
        show_welcome_message()
        # 启动主事件循环（传入ACC代理实例）
        await run_main_loop(system_state["acc_agent"])
        return 0  # 正常退出码
    except Exception as e:
        # 捕获未处理异常，记录详细错误信息
        import sys

        _, exc_obj, exc_tb = sys.exc_info()
        error_file = exc_tb.tb_frame.f_code.co_filename  # 获取出错文件路径
        error_msg = f"错误文件: {error_file}\n错误内容: {str(exc_obj)}"
        logging.error(error_msg)
        print(error_msg)  # 在控制台额外输出错误
        return 1  # 异常退出码
    finally:
        # 确保关闭所有MCP连接
        try:
            if system_state and "mcp_manager" in system_state:
                await system_state["mcp_manager"].close_all()
        except Exception as e:
            error_msg = f"关闭连接时出错: {str(e)}"
            logging.error(error_msg)
            print(error_msg)


def main():
    """同步入口函数
    作用：启动异步事件循环并返回退出码
    """
    return asyncio.run(async_main())


# Windows打包可执行文件时需要__main__入口
if __name__ == "__main__":
    sys.exit(main())  # 将程序退出码传递给系统
