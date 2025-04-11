# Auto-Central-Control 🤖  

[![GitHub License](https://img.shields.io/github/license/Love-AronaPlana/Auto-Central-Control?style=flat-square)](LICENSE)  
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square)](https://www.python.org/)  
[![Project Status](https://img.shields.io/badge/Status-Beta-green?style=flat-square)](https://github.com/Love-AronaPlana/ACC)  


## 🔥 项目概述  
Auto-Central-Control (ACC) 是一个基于 **MCP (Model Context Protocol)** 的模块化自动化控制系统，通过统一接口集成文件系统操作、Excel 处理、Web 浏览等服务。系统采用可扩展架构，支持动态接入多种 MCP 服务器，实现功能的灵活组合与高效管理。  

ACC 旨在解决多系统集成的复杂性问题，让用户能够通过简单的配置和自然语言指令，实现跨平台、跨应用的自动化工作流程。无论是数据处理、文档管理还是网页交互，ACC 都能提供一站式解决方案。  


## 📁 代码结构  
```plaintext  
Auto-Central-Control/  
├── ACC/                        # 核心代码目录  
│   ├── agent/                  # LLM 交互代理模块  
│   │   ├── agent.py            # 代理核心实现  
│   │   └── prompt.py           # 代理提示词管理  
│   ├── config.py               # 配置加载与管理  
│   ├── core/                   # 核心功能  
│   │   ├── discovery.py        # 工具发现机制  
│   │   ├── registry.py         # 工具注册中心  
│   │   └── executor.py         # 工具执行引擎  
│   ├── function/               # 基础功能函数  
│   │   ├── file_utils.py       # 文件操作工具  
│   │   └── string_utils.py     # 字符串处理工具  
│   ├── interaction/            # 用户交互模块  
│   │   ├── cli.py              # 命令行交互界面  
│   │   └── web.py              # Web交互界面  
│   ├── llm.py                  # 大语言模型接口  
│   ├── local_tools/            # 本地工具集合  
│   ├── mcp.py                  # MCP 服务器管理核心  
│   ├── memory/                 # 内存与状态管理  
│   │   ├── context.py          # 上下文管理  
│   │   └── history.py          # 历史记录管理  
│   ├── prompt/                 # 提示词模板库  
│   ├── system/                 # 系统初始化模块  
│   │   ├── bootstrap.py        # 系统引导程序  
│   │   └── health.py           # 系统健康检查  
│   └── workflow.py             # 工作流引擎  
├── config/                     # 配置文件  
│   ├── config.toml             # 主配置（含示例模板）  
│   ├── config.example.toml     # 配置模板  
│   └── mcp_server.json         # MCP 服务器配置  
├── logs/                       # 日志存储  
├── main.py                     # 程序主入口  
├── mcp_server_files/           # MCP 服务器文件（第三方）  
│   ├── excel/                  # Excel 处理服务器  
│   ├── excel-mcp-server-main/  # Excel MCP 服务器主程序  
│   └── web-browser/            # Web 浏览器服务器  
├── requirements.txt            # 依赖清单  
├── start.py                    # 一键启动脚本  
└── workspace/                  # 运行时工作目录  
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

#### 连接方式详解  
1. **标准 stdio 服务器**：通过标准输入输出流与服务器通信，适合简单的命令行工具  
2. **SSE 类型服务器**：使用 Server-Sent Events 技术实现实时通信，适合需要持续数据流的场景  
3. **远程 SSE 服务器**：直接连接远程 SSE 服务，无需本地部署，适合云服务集成  


## 🚀 MCP 服务器管理  
### 什么是 MCP 服务器？  
MCP (Model Context Protocol) 服务器是提供特定功能的服务单元（如文件操作、数据处理），通过 MCP 协议与 ACC 通信，实现功能解耦与动态扩展。  

MCP 协议的核心优势：  
- **统一接口**：所有服务器遵循相同的通信协议  
- **动态发现**：系统可自动发现并注册服务器提供的工具  
- **上下文共享**：服务器之间可共享上下文，实现无缝协作  
- **安全隔离**：每个服务器在独立进程中运行，提高系统稳定性  

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
        "C:\\Users\\Username",  
        "C:\\Users\\Username\\Desktop"  
      ]  
    }  
  }  
}  
```  
- **配置项**：`command`（启动命令）、`args`（参数列表）  
- **步骤**：修改 `mcp_server.json` → 添加服务器名称及参数 → 重启系统  
- **适用场景**：文件系统操作、简单的系统命令执行等  

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
- **适用场景**：需实时通信的服务（如 Excel 数据监听、实时数据处理）  
- **优势**：支持长连接、事件推送，适合需要持续数据流的场景  

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
- **配置项**：远程服务器 URL、传输方式  
- **优势**：无需本地部署，直接接入第三方服务  
- **适用场景**：云服务集成、第三方API调用等  

### 服务器状态监控  
ACC 提供了完善的服务器状态监控机制：  
- **自动重连**：检测到断开连接时自动尝试重连  
- **日志记录**：详细记录服务器通信日志，便于问题排查  


## 🚦 启动与运行  
### 1. 环境要求  
- Python 3.8 或更高版本  
- 支持 Windows、macOS 和 Linux 系统  
- 网络连接（用于 LLM API 调用和远程服务器连接）  

### 2. 安装依赖  
```bash  
pip install -r requirements.txt  
```  

### 3. 配置系统  
1. 复制 `config/config.example.toml` 到 `config/config.toml`  
2. 编辑 `config.toml`，设置 LLM API 密钥和其他必要参数  
3. 根据需要修改 `config/mcp_server.json` 配置 MCP 服务器  

### 4. 启动系统  
```bash  
python start.py  
```  

#### 启动流程详解  
1. **加载配置**：读取并验证配置文件  
2. **初始化日志**：设置日志级别和输出目标  
3. **初始化工作流引擎**：创建工作流执行环境  
4. **连接 MCP 服务器**：根据配置连接各 MCP 服务器  
5. **自动发现工具**：从 MCP 服务器发现可用工具  
6. **注册功能到代理**：将工具注册到 LLM 代理  
7. **启动用户界面**：初始化命令行或 Web 交互界面  

#### 命令行参数  
```bash  
python start.py --help  
```  
支持的命令行参数：  
- `--config`: 指定配置文件路径  
- `--debug`: 启用调试模式  
- `--no-mcp`: 禁用 MCP 服务器连接  
- `--web`: 启用 Web 界面（默认使用命令行界面）  


## 🛠️ 开发与扩展  
### 添加新 MCP 服务器  
1. 实现服务器逻辑（支持 stdio/SSE 协议）  
2. 在 `mcp_server.json` 中添加配置  
3. 重启系统完成自动发现  

### 自定义工作流程  
修改 `ACC/workflow.py`，通过定义 `Workflow` 类实现个性化逻辑，支持事件监听、任务调度等功能。  

### 开发本地工具  
1. 在 `ACC/local_tools/` 目录下创建新的工具模块  
2. 实现工具函数并添加适当的文档字符串  
3. 在 `ACC/local_tools/__init__.py` 中注册工具  
4. 重启系统，新工具将自动被发现并注册  

### 扩展代理能力  
1. 修改 `ACC/agent/prompt.py` 中的提示词模板  
2. 调整 `ACC/agent/agent.py` 中的代理逻辑  
3. 在 `ACC/prompt/` 目录下添加新的提示词模板  

### 插件系统  
ACC 支持通过插件机制扩展功能：  
1. 在 `plugins/` 目录下创建新插件  
2. 实现插件的 `register()` 和 `initialize()` 方法  
3. 在配置文件中启用插件  
4. 重启系统，插件将被自动加载  

### 错误处理  
- **自动重试**：遇到临时错误时自动重试  
- **优雅降级**：核心功能出错时提供备选方案  
- **详细日志**：记录详细的错误信息，便于问题排查  


## ❓ 常见问题  
| 问题描述                | 解决方案                                                                 |  
|-------------------------|--------------------------------------------------------------------------|  
| MCP 服务器连接失败      | 检查命令路径、端口占用、网络连接；验证配置参数是否正确                   |  
| 工具发现失败            | 确保服务器已正确启动并支持工具发现协议；调整超时时间（`config.toml`）    |  
| 依赖安装报错            | 确认 Python 版本 ≥ 3.8；尝试使用 `pip install --no-cache-dir -r requirements.txt` |  
| LLM API 调用失败        | 检查 API 密钥是否正确；确认网络连接；查看 API 额度是否用尽              |  
| 系统响应缓慢            | 调整并行度设置；检查是否有资源密集型任务；考虑升级硬件配置              |  
| 工作流执行中断          | 查看日志确认错误原因；检查工作流定义是否正确；确保所有依赖服务可用      |  
| 内存占用过高            | 调整上下文窗口大小；减少并行任务数量；启用内存优化选项                  |  
| 配置文件加载失败        | 检查配置文件格式是否正确；确保所有必填项都已设置；尝试使用默认配置      |  


## 🔒 安全与隐私  
ACC 高度重视安全与隐私保护：  
- **数据隔离**：每个 MCP 服务器在独立进程中运行，确保数据隔离  
- **最小权限**：遵循最小权限原则，每个组件只能访问必要的资源  
- **加密通信**：支持 HTTPS/WSS 加密通信，保护数据传输安全  
- **本地处理**：敏感数据优先在本地处理，减少数据传输  
- **审计日志**：记录关键操作的审计日志，便于安全审计  


## 🌐 社区与贡献  
我们欢迎社区贡献，您可以通过以下方式参与：  
- **提交 Issue**：报告 bug 或提出功能建议  
- **提交 PR**：贡献代码改进或新功能  
- **编写文档**：完善项目文档  
- **分享经验**：在社区中分享使用经验和最佳实践  

### 贡献指南  
1. Fork 项目仓库  
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)  
3. 提交更改 (`git commit -m 'Add amazing feature'`)  
4. 推送到分支 (`git push origin feature/amazing-feature`)  
5. 创建 Pull Request  


## 📜 文档版本  
**文档版本**：v0.1.0（2025-04-11）  
**项目地址**：[https://github.com/Love-AronaPlana/ACC](https://github.com/Love-AronaPlana/ACC)  


## 📄 许可证  
本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。  

  
*Powered by MCP Protocol & ACC开发组* 🌟  
