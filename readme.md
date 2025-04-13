# Auto-Central-Control 🤖  

[![GitHub License](https://img.shields.io/github/license/Love-AronaPlana/Auto-Central-Control?style=flat-square)](LICENSE)  
[![Python Version](https://www.python.org/static/community_logos/python-3.8.10.svg)](https://www.python.org/)  
[![Project Status](https://img.shields.io/badge/Status-Beta-green?style=flat-square)](https://github.com/Love-AronaPlana/ACC)  


## 🔥 项目概述  
Auto-Central-Control (ACC) 是一个基于 **MCP (Model Context Protocol)** 的模块化自动化控制系统，通过统一接口集成文件系统操作、Excel 处理、Web 浏览等服务。系统采用可扩展架构，支持动态接入多种 MCP 服务器，实现功能的灵活组合与高效管理。  

ACC 旨在解决多系统集成的复杂性问题，让用户能够通过简单的配置和自然语言指令，实现跨平台、跨应用的自动化工作流程。无论是数据处理、文档管理还是网页交互，ACC 都能提供一站式解决方案。  


## 📁 代码结构  
```plaintext  
Auto-Central-Control/  
├── ACC/                        # 核心代码目录  
│   ├── agent/                  # LLM 交互代理模块  
│   │   └── __init__.py         # 代理初始化与接口导出  
│   ├── config.py               # 配置加载与管理  
│   ├── core/                   # 核心功能  
│   │   ├── runner.py           # 主运行循环模块  
│   │   └── tool_discovery.py   # 工具发现机制  
│   ├── function/               # 基础功能函数  
│   │   ├── use_tool.py         # 工具调用模块  
│   │   ├── search_tool_info.py # 工具信息查询  
│   │   ├── print_for_user.py   # 用户信息输出  
│   │   └── get_user_input.py   # 用户输入处理  
│   ├── interaction/            # 用户交互模块  
│   │   └── cli.py              # 命令行交互界面  
│   ├── llm.py                  # 大语言模型接口  
│   ├── local_tools/            # 本地工具集合  
│   ├── mcp.py                  # MCP 服务器管理核心  
│   ├── memory/                 # 内存与状态管理  
│   ├── prompt/                 # 提示词模板库  
│   │   ├── __init__.py         # 提示词模块导出  
│   │   └── ACC.py              # 系统提示词定义  
│   ├── system/                 # 系统初始化模块  
│   │   └── initializer.py      # 系统初始化器  
│   └── workflow.py             # 工作流引擎  
├── config/                     # 配置文件  
│   ├── config.example.toml     # 配置模板  
│   └── mcp_server.json         # MCP 服务器配置  
├── logs/                       # 日志存储  
├── mcp_server_files/           # MCP 服务器文件（第三方）  
│   ├── excel/                  # Excel 处理服务器  
├── requirements.txt            # 依赖清单  
├── start.py                    # 一键启动脚本  
├── start_mcp_server.py         # MCP服务器启动脚本  
└── start_mcp_server.bat        # MCP服务器启动批处理文件（Windows）  
```  


## ⚙️ 系统配置  
### 基础配置  
- **主配置文件**：`config/config.toml`  
  包含系统运行参数（如端口、日志级别、LLM 配置等）。首次运行时若文件不存在，将自动根据 `config.example.toml` 生成模板。  

- **配置项说明**：  
  - `system`: 系统全局设置（日志级别、工作目录等）  
  - `llm`: 大语言模型配置（API密钥、模型名称、温度等）  
  - `agent`: 代理配置（最大历史记录、上下文窗口等）  
  - `mcp`: MCP服务器配置（超时时间、重试次数等）  
  - `workflow`: 工作流配置（并行度、队列大小等）  

### MCP 服务器配置  
通过 `config/mcp_server.json` 定义可接入的 MCP 服务器，支持三种连接方式：  

#### 配置文件中的通配符  
在 `mcp_server.json` 中，您可以使用 `{UserName}` 通配符表示当前系统用户名。系统启动时自动替换为实际用户名，便于跨用户环境部署。例如：  
```json  
{  
  "args": [  
    "@modelcontextprotocol/server-filesystem",  
    "C:\\Users\\{UserName}",  
    "C:\\Users\\{UserName}\\Desktop"  
  ]  
}  
```  
上述配置运行时会自动替换为 `C:\Users\John` 和 `C:\Users\John\Desktop` 等实际路径。  


## 🚀 MCP 服务器管理  
### 什么是 MCP 服务器？  
MCP (Model Context Protocol) 服务器是提供特定功能的服务单元（如文件操作、数据处理），通过 MCP 协议与 ACC 通信，实现功能解耦与动态扩展。  

**核心优势**：  
- **统一接口**：所有服务器遵循相同通信协议  
- **动态发现**：系统自动发现并注册服务器工具  
- **上下文共享**：服务器间可共享上下文实现无缝协作  
- **安全隔离**：每个服务器在独立进程中运行提升稳定性  

### 添加服务器指南  
#### 1. 标准 stdio 服务器（命令行交互）  
```json  
{  
  "mcpServers": {  
    "filesystem": {  
      "command": "npx",  
      "args": [  
        "-y",  
        "--registry=https://registry.npmmirror.com",  
        "@modelcontextprotocol/server-filesystem",  
        "C:\\Users\\{UserName}",  
        "C:\\Users\\{UserName}\\Desktop"  
      ]  
    }  
  }  
}  
```  
- **配置项**：`command`（启动命令）、`args`（参数列表）  
- **步骤**：修改配置文件 → 添加服务器名称及参数 → 重启系统  
- **适用场景**：文件系统操作、简单系统命令执行  

#### 2. SSE 类型服务器（HTTP 长连接）  
```json  
{  
  "mcpServers": {  
    "excel": {  
      "stdio_command": "uv",  
      "stdio_args": ["run", "excel-mcp-server"],  
      "port": 8000,  
      "transport": "sse"  
    }  
  }  
}  
```  
- **配置项**：启动命令、端口、传输方式（`sse`）  
- **适用场景**：实时通信服务（Excel数据监听、实时数据处理）  
- **优势**：支持长连接与事件推送，适合持续数据流场景  

#### 3. 远程 SSE 服务器（直接 URL 连接）  
```json  
{  
  "mcpServers": {  
    "mathall": {  
      "url": "http://mcp.example.com/sse",  
      "transport": "sse"  
    }  
  }  
}  
```  
- **配置项**：远程服务器URL、传输方式  
- **优势**：无需本地部署，直接接入第三方服务  
- **适用场景**：云服务集成、第三方API调用  


## 🚦 启动与运行  
### 1. 环境要求  
- **Python 3.8+**  
- 支持 Windows/macOS/Linux  
- 网络连接（LLM API调用与远程服务器连接）  

### 2. 安装依赖  
```bash  
pip install -r requirements.txt  
```  

### 3. 配置系统  
1. 复制 `config/config.example.toml` 到 `config/config.toml`  
2. 编辑配置文件，设置LLM API密钥及必要参数  
3. 根据需求修改 `config/mcp_server.json` 配置MCP服务器  

### 4. 启动系统  
**分步启动说明**：  
#### 步骤一：启动MCP服务器  
```bash  
# Windows系统  
start_mcp_server.bat  

# 通用启动命令  
python start_mcp_server.py  
```  
*等待控制台输出 "MCP服务器初始化完成"*  

#### 步骤二：启动主程序  
```bash  
python start.py  
```  

#### 启动流程详解  
1. **MCP服务器启动**：  
   - 加载配置并替换 `{UserName}` 通配符  
   - 启动服务器进程并注册可用工具  
2. **主程序启动**：  
   - 加载验证配置 → 初始化日志系统  
   - 启动工作流引擎 → 连接MCP服务器  
   - 注册工具到LLM代理  


## 🛠️ 开发与扩展  
### 添加新MCP服务器  
1. 实现服务器逻辑（支持stdio/SSE协议）  
2. 在 `mcp_server.json` 中添加配置  
3. 重启系统完成自动发现  

### 开发本地工具  
1. 在 `ACC/local_tools/` 目录创建新工具模块  
2. 实现工具函数并添加文档注释  
3. 重启系统自动注册新工具  


## ❓ 常见问题  
| 问题描述              | 解决方案                                                                 |  
|-----------------------|--------------------------------------------------------------------------|  
| MCP服务器连接失败      | 检查命令路径/端口占用/网络连接，验证配置参数正确性                       |  
| 工具发现失败          | 确保服务器正确启动并支持工具发现协议                                     |  
| 依赖安装报错          | 确认Python≥3.8，尝试 `pip install --no-cache-dir -r requirements.txt`     |  
| LLM API调用失败       | 检查API密钥/网络连接，确认API额度未用尽                                   |  
| 系统响应缓慢          | 调整并行度设置，检查资源占用任务，考虑硬件升级                           |  
| 工作流执行中断        | 查看日志定位错误，检查工作流定义及依赖服务状态                           |  
| 内存占用过高          | 调整上下文窗口大小，减少并行任务，启用内存优化选项                       |  
| 配置文件加载失败      | 检查文件格式/必填项设置，尝试使用默认配置                               |  
| 通配符替换失败        | 确认 `{UserName}` 格式正确，检查系统环境变量获取用户名                   |  


## 🌐 社区与贡献  
欢迎通过以下方式参与项目：  
- **提交Issue**：报告Bug或提出功能建议  
- **提交PR**：贡献代码改进或新功能  
- **完善文档**：优化项目文档提升可读性  
- **经验分享**：在社区传播使用经验和最佳实践  

### 贡献指南  
1. Fork项目仓库  
2. 创建功能分支：`git checkout -b feature/new-function`  
3. 提交更改：`git commit -m 'Add new feature description'`  
4. 推送分支：`git push origin feature/new-function`  
5. 创建Pull Request  


## 📜 文档版本  
- **文档版本**：v0.1.2（2025-04-13）  
- **项目地址**：[https://github.com/Love-AronaPlana/ACC](https://github.com/Love-AronaPlana/ACC)  


## 📄 许可证  
本项目采用 **MIT许可证**，详情请参阅 [LICENSE](LICENSE) 文件。  

  
*Powered by MCP Protocol & ACC开发组* 🌟  