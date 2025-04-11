# -*- coding: utf-8 -*-

"""对话历史记录管理模块

该模块负责:
1. 存储和管理系统与LLM的对话历史
2. 提供历史记录的读写接口
3. 在每次会话开始时清空历史记录
"""

import json
import os
import logging
from typing import List, Dict, Any

# 配置日志记录器
logger = logging.getLogger(__name__)


class HistoryManager:
    """对话历史记录管理类"""

    def __init__(self):
        """初始化历史记录管理器"""
        # 历史记录文件路径
        self.history_file = os.path.join(os.path.dirname(__file__), "history.json")
        # 内存中的历史记录
        self.history = []
        # 是否已经添加了系统提示词
        self.system_prompt_added = False

        # 清空历史记录文件
        self.clear_history()

        logger.info("历史记录管理器初始化完成")

    def clear_history(self) -> None:
        """清空历史记录"""
        self.history = []
        self.system_prompt_added = False

        # 创建空的历史记录文件
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

        logger.info("历史记录已清空")

    def add_message(self, role: str, content: str) -> None:
        """添加一条消息到历史记录

        Args:
            role: 消息角色 (system, user, assistant)
            content: 消息内容
        """
        # 如果是系统消息且已经添加过系统提示词，则不再添加
        if role == "system" and self.system_prompt_added:
            return

        # 添加消息到内存中的历史记录
        message = {"role": role, "content": content}
        self.history.append(message)

        # 如果是系统消息，标记已添加系统提示词
        if role == "system":
            self.system_prompt_added = True

        # 保存到文件
        self._save_history()

        logger.debug(f"添加{role}消息到历史记录: {content[:50]}...")

    def ensure_system_prompt(self, system_prompt: str) -> None:
        """确保系统提示词已添加到历史记录中
        
        如果系统提示词尚未添加，则添加它作为第一条消息
        
        Args:
            system_prompt: 系统提示词内容
        """
        if not self.system_prompt_added:
            # 保存当前历史记录
            current_history = self.history.copy()
            # 清空历史记录
            self.history = []
            # 添加系统提示词作为第一条消息
            self.add_message("system", system_prompt)
            # 将原有历史记录添加回来
            for message in current_history:
                self.history.append(message)
            # 保存到文件
            self._save_history()
            logger.info("已将系统提示词添加为第一条消息")

    def get_history(self) -> List[Dict[str, str]]:
        """获取历史记录

        Returns:
            历史记录消息列表
        """
        return self.history

    def _save_history(self) -> None:
        """保存历史记录到文件"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存历史记录失败: {str(e)}")


# 创建全局历史记录管理器实例
_history_manager = None


def get_history_manager() -> HistoryManager:
    """获取历史记录管理器实例

    Returns:
        历史记录管理器实例
    """
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
    return _history_manager
