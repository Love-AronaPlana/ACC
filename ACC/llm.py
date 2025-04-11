# -*- coding: utf-8 -*-

"""ACC LLM接口模块

该模块负责:
1. 提供统一的LLM请求接口
2. 处理API请求和响应
3. 管理模型上下文
"""

import json
import logging
import requests
import re
import time
from typing import Dict, Any, List, Optional

from .config import get_value
from .memory.history import get_history_manager
from .prompt.ACC import MISS_FUCTION  # 导入MISS_FUCTION提示词

# 配置日志记录器
logger = logging.getLogger(__name__)


class LLMInterface:
    """LLM接口类，负责与OpenAI API通信"""

    def __init__(self):
        """初始化LLM接口"""
        # 从配置中获取API信息
        self.model = get_value("llm", "model")
        self.base_url = get_value("llm", "base_url")
        self.api_key = get_value("llm", "api_key")
        self.max_tokens = get_value("llm", "max_tokens")
        self.temperature = get_value("llm", "temperature", 0.3)
        self.debug = get_value("llm", "debug", False)
        
        # 视觉模型配置
        self.vision_model = get_value("llm.vision", "model")
        self.vision_base_url = get_value("llm.vision", "base_url")
        self.vision_api_key = get_value("llm.vision", "api_key")
        
        # 视觉功能开关
        self.enable_vision = get_value("vision.enable", "enable_vision", False)
        
        # 重试配置
        self.max_retries = 10
        self.retry_delay = 10  # 秒

        # 验证必要的配置项
        if not all([self.model, self.base_url, self.api_key]):
            raise ValueError("LLM配置不完整，请检查配置文件")

        logger.info(f"LLM接口初始化完成，使用模型: {self.model}")
        if self.enable_vision:
            logger.info(f"视觉功能已启用，使用模型: {self.vision_model}")

    def send_request(
        self,
        messages: List[Dict[str, Any]],
        image_base64: Optional[str] = None,
    ) -> Dict[str, Any]:
        """发送请求到LLM API，支持网络错误重试
    
        Args:
            messages: 消息列表，包含角色和内容
            image_base64: 可选的base64编码图片
    
        Returns:
            API响应的JSON对象
    
        Raises:
            Exception: 所有重试都失败后抛出异常
        """
        # 确定是否使用视觉模型
        use_vision_model = False
        
        # 如果提供了图片且视觉功能已启用，则使用视觉模型
        if image_base64 and self.enable_vision:
            use_vision_model = True
            model = self.vision_model
            base_url = self.vision_base_url
            api_key = self.vision_api_key
        else:
            model = self.model
            base_url = self.base_url
            api_key = self.api_key
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        
        # 如果提供了图片且视觉功能已启用，修改最后一条用户消息以包含图片
        if image_base64 and self.enable_vision:
            for i in range(len(messages) - 1, -1, -1):
                if messages[i]["role"] == "user":
                    # 确保content是列表格式
                    if isinstance(messages[i]["content"], str):
                        messages[i]["content"] = [{"type": "text", "text": messages[i]["content"]}]
                    elif isinstance(messages[i]["content"], list):
                        pass  # 已经是列表格式
                    else:
                        messages[i]["content"] = [{"type": "text", "text": str(messages[i]["content"])}]
                    
                    # 添加图片内容
                    messages[i]["content"].append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    })
                    break
    
        # 构建请求体
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
    
        # 调试模式下打印请求信息
        if self.debug:
            logger.debug(f"完整请求URL: {base_url}/chat/completions")
            logger.debug(
                "完整请求头:\n" + json.dumps(headers, indent=2, ensure_ascii=False)
            )
            logger.debug(
                "完整请求体:\n"
                + json.dumps(payload, indent=2, ensure_ascii=False, default=str)
            )
            if use_vision_model:
                logger.debug("使用视觉模型进行请求")
    
        # 实现重试机制
        retry_count = 0
        last_exception = None
        
        while retry_count < self.max_retries:
            try:
                # 发送请求
                response = requests.post(
                    f"{base_url}/chat/completions", headers=headers, json=payload
                )
    
                # 检查响应状态
                response.raise_for_status()
    
                # 解析响应
                result = response.json()
    
                # 调试模式下打印原始响应
                if self.debug:
                    logger.debug(
                        "原始API响应:\n" + json.dumps(result, indent=2, ensure_ascii=False)
                    )
    
                return result
                
            except (requests.RequestException, requests.ConnectionError, 
                    requests.Timeout, requests.HTTPError) as e:
                # 记录网络错误
                retry_count += 1
                last_exception = e
                
                if retry_count < self.max_retries:
                    logger.warning(
                        f"API请求失败 (尝试 {retry_count}/{self.max_retries}): {str(e)}，"
                        f"{self.retry_delay}秒后重试..."
                    )
                    time.sleep(self.retry_delay)
                else:
                    logger.error(
                        f"API请求失败，已达到最大重试次数 ({self.max_retries}): {str(e)}"
                    )
            except Exception as e:
                # 非网络错误直接抛出
                logger.error(f"API请求发生非网络错误: {str(e)}")
                raise
        
        # 所有重试都失败
        logger.error(f"所有重试都失败，最后一次错误: {str(last_exception)}")
        raise last_exception or Exception("API请求失败，所有重试均未成功")

    def _check_and_retry_invalid_function(self, content_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        检查function值是否有效，如果无效则重新发送MISS_FUCTION提示词
        
        Args:
            content_json: 解析后的JSON内容
            
        Returns:
            如果需要重试，返回重试后的响应；否则返回None
        """
        valid_functions = ["search_tool_info", "print_for_user", "need_user_input", "use_tool", "tool_list"]
        
        # if (isinstance(content_json, dict) and 
        #     "function" in content_json and 
        #     content_json["function"] not in valid_functions):
            
        #     logger.warning(f"检测到无效的function值: {content_json['function']}，将重新发送MISS_FUCTION提示词")
            
        #     # 获取历史记录管理器
        #     history_manager = get_history_manager()
            
        #     # 获取完整的历史对话记录
        #     history = history_manager.get_history()
            
        #     # 创建新的消息列表，保留所有历史记录
        #     messages = []
            
        #     # 添加系统提示词作为第一条消息
        #     messages.append({"role": "system", "content": MISS_FUCTION})
        
            
        #     logger.debug(f"重新发送请求，包含 {len(messages)} 条消息")
            
        #     # 发送包含完整历史记录的请求
        #     retry_response = self.send_request(messages)
            
        #     # 递归调用解析新响应
        #     return self.parse_response(retry_response)
        
        return None

    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.debug:
                logger.debug("开始解析API响应...")
                logger.debug(
                    f"原始响应数据结构:\n{json.dumps(response, indent=2, ensure_ascii=False)}"
                )
    
            # 获取响应中的消息内容
            message = response.get("choices", [{}])[0].get("message", {})
            
            # 处理新格式的content（可能是字符串或数组）
            content = ""
            if isinstance(message.get("content"), str):
                content = message.get("content", "")
            elif isinstance(message.get("content"), list):
                # 如果content是数组，合并所有text类型的内容
                for item in message.get("content", []):
                    if item.get("type") == "text":
                        content += item.get("text", "")
            
            # 将助手回复添加到历史记录
            if content:
                history_manager = get_history_manager()
                history_manager.add_message("assistant", content)
    
            # 检查是否有工具调用
            if "tool_calls" in message:
                tool_call = message["tool_calls"][0]
                try:
                    # 尝试解析工具调用中的函数参数
                    function_args = json.loads(tool_call["function"]["arguments"])
                    # 将function名称添加到参数中
                    function_args["function"] = tool_call["function"]["name"]
                    
                    # 检查function值是否有效，如果无效则重试
                    retry_result = self._check_and_retry_invalid_function(function_args)
                    if retry_result:
                        return retry_result
                        
                    return function_args
                except json.JSONDecodeError:
                    return {"type": "tool_calls", "tool_calls": message["tool_calls"]}
    
            # 检查是否有普通内容
            if content:
                # 检查内容是否包含在Markdown代码块中
                json_match = re.search(r"```(?:json)?\n(.*?)\n```", content, re.DOTALL)
                if json_match:
                    # 提取JSON内容
                    json_content = json_match.group(1)
                    try:
                        content_json = json.loads(json_content)
                        # 确保返回的是一个包含function字段的字典
                        if (
                            isinstance(content_json, dict)
                            and "function" in content_json
                        ):
                            # 检查function值是否有效，如果无效则重试
                            retry_result = self._check_and_retry_invalid_function(content_json)
                            if retry_result:
                                return retry_result
                                
                            return content_json
                        else:
                            return {"type": "json", "content": content_json}
                    except json.JSONDecodeError:
                        # 如果提取的内容不是有效JSON，返回原始内容
                        return {"type": "text", "content": content}
    
                # 如果不在代码块中，尝试直接解析
                try:
                    content_json = json.loads(content)
                    if (
                        isinstance(content_json, dict)
                        and "function" in content_json
                    ):
                        # 检查function值是否有效，如果无效则重试
                        retry_result = self._check_and_retry_invalid_function(content_json)
                        if retry_result:
                            return retry_result
                            
                        return content_json
                    else:
                        return {"type": "json", "content": content_json}
                except json.JSONDecodeError:
                    # 如果不是有效JSON，返回原始内容
                    return {"type": "text", "content": content}
    
            # 如果没有内容，返回空响应
            return {"type": "empty", "content": ""}
        except Exception as e:
            logger.error(f"解析API响应时出错: {str(e)}")
            return {"type": "error", "content": str(e)}


# 创建全局LLM接口实例
_llm_interface = None


def get_llm_interface() -> LLMInterface:
    """获取LLM接口实例

    Returns:
        LLM接口实例
    """
    global _llm_interface
    if _llm_interface is None:
        _llm_interface = LLMInterface()
    return _llm_interface


def send_message(
    system_prompt: str,
    user_message: Any,
    tools: Optional[List[Dict[str, Any]]] = None,
    user_status: str = None,
    image_base64: Optional[str] = None,
) -> Dict[str, Any]:
    """发送消息到LLM并获取响应

    Args:
        system_prompt: 系统提示
        user_message: 用户消息
        tools: 可选的工具列表 (不再使用)
        user_status: 用户状态名称，默认为None
        image_base64: 可选的base64编码图片

    Returns:
        解析后的响应内容
    """
    # 获取LLM接口实例
    llm = get_llm_interface()

    # 获取历史记录管理器
    history_manager = get_history_manager()

    # 获取历史记录管理器
    history_manager = get_history_manager()
    
    # 添加日志记录图片状态
    if image_base64 and llm.enable_vision:
        logger.info("检测到图片输入，将使用视觉模型处理请求")
    elif image_base64 and not llm.enable_vision:
        logger.warning("检测到图片输入，但视觉功能未启用，图片将被忽略")
        
    # 处理用户消息，确保它是字符串类型
    if isinstance(user_message, dict):
        # 如果是字典类型，提取content字段或转换为JSON字符串
        if "content" in user_message:
            formatted_user_message = user_message["content"]
        else:
            formatted_user_message = json.dumps(user_message, ensure_ascii=False)
    else:
        formatted_user_message = str(user_message)

    # 格式化用户消息和提示词
    message_content = []
    
    # 添加用户消息作为第一个text对象
    message_content.append({
        "type": "text",
        "text": formatted_user_message
    })
    
    # 如果有用户状态，添加提示词作为第二个text对象
    if user_status:
        from .prompt.user import USER_PROMPT
        
        prompt_text = USER_PROMPT.replace(
            "{{user_status_name}}", user_status
        )
        
        message_content.append({
            "type": "text",
            "text": prompt_text
        })
    
    # 创建新格式的用户消息
    structured_user_message = {
        "role": "user",
        "content": message_content
    }

    # 添加用户消息到历史记录（为了兼容性，仍然保存为文本格式）
    history_text = formatted_user_message
    if user_status:
        from .prompt.user import USER_PROMPT
        history_text += "\n" + USER_PROMPT.replace("{{user_status_name}}", user_status)
    
    history_manager.add_message("user", history_text)

    # 如果历史记录为空，添加系统提示词
    if not history_manager.system_prompt_added:
        history_manager.add_message("system", system_prompt)

    # 获取完整的历史记录并转换为新格式
    old_messages = history_manager.get_history()
    messages = []
    
    for msg in old_messages:
        if msg["role"] == "user" and msg == old_messages[-1]:
            # 替换最后一条用户消息为新格式
            messages.append(structured_user_message)
        elif msg["role"] == "system":
            # 系统消息保持原样
            messages.append(msg)
        elif msg["role"] == "assistant":
            # 助手消息保持原样
            messages.append(msg)
        else:
            # 其他用户消息也转换为新格式
            old_content = msg.get("content", "")
            messages.append({
                "role": "user",
                "content": [{"type": "text", "text": old_content}]
            })
    
    # 发送请求，可能包含图片
    response = llm.send_request(messages, image_base64=image_base64)

    # 解析响应
    return llm.parse_response(response)