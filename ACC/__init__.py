# -*- coding: utf-8 -*-

"""ACC核心模块

该模块是Auto-Central-Control系统的核心，提供了基础功能和接口。
"""

# 导出主要组件
from .config import load_config, get_config, get_value
from .llm import LLMInterface, get_llm_interface, send_message
from .workflow import WorkflowManager, get_workflow_manager

# 添加 ↓
from .core.runner import run_main_loop
from .interaction.cli import get_user_input, show_response, show_error
