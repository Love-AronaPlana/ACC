# -*- coding: utf-8 -*-

USER_PROMPT = """"user_status": "{{user_status_name}}",
Please reply strictly in json format. The json format should be as follows:
{{
  "plan": "[steps array with id and title fields]",
  "status": "[next task description, a complete sentence tell user what to do next]",
  "function": "[movement]",
  "value": "[value of function]",
  "tool_value": "[value of use_tool]"
}}
"""
