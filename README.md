# 辩论系统 / AI Debate System

多智能体 AI 辩论平台，支持辩论双方观点碰撞、实时研究数据聚合、投票统计与用户参与。

## 功能特性

- 🤖 **多智能体辩论** — 每次辩论由多个角色（研究员、质疑者、乐观派、务实派等）组成辩论小组
- 🔍 **实时研究** — 自动抓取维基百科、财经数据、学术论文、GitHub 等真实来源
- 🗳️ **投票系统** — AI 投票统计 + 用户参与投票，对比人机判断差异
- 📊 **辩论报告** — 完整辩论流程记录，支持导出 Markdown 报告
- 🔗 **多 API 支持** — MiniMax / DeepSeek / OpenAI / Anthropic / Google Gemini / Groq 等

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `config.example.py` 为 `config.py`，填入你的 API Key：

```python
MINIMAX_API_KEY = "your_key_here"
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
MINIMAX_MODEL = "MiniMax-M2.7"
```

**或**通过环境变量（推荐）：

```bash
export MINIMAX_API_KEY="your_key_here"
python start.py
```

### 3. 启动服务

```bash
python start.py
# 访问 http://localhost:8098/debate
```

## 项目结构

```
辩论/
├── server.py          # FastAPI 服务器，API 路由
├── agents.py          # 辩论智能体编排
├── researcher.py      # 研究数据抓取层
├── store.py           # 内存会话存储
├── minimax.py         # MiniMax API 客户端
├── config.example.py  # 配置模板
├── start.py           # 启动入口
├── templates/
│   └── debate.html    # 前端辩论界面
```

## 辩论流程

1. **策划** — 主策划 LLM 设计辩论小组结构和角色
2. **研究** — 并行抓取多源真实数据（无 API Key 的免费来源）
3. **辩论** — 多轮讨论，每轮各 agent 轮流发言
4. **投票** — AI agent 投票 + 用户投票，统计立场分布
5. **总结** — 主策划综合所有观点，给出最终结论

## 支持的 API Provider

| Provider | API Format | 推荐场景 |
|----------|-----------|---------|
| MiniMax | Anthropic | 默认，快速中文支持 |
| DeepSeek | OpenAI | 性价比高 |
| OpenAI | OpenAI | GPT-4o |
| Anthropic | Anthropic Direct | Claude 系列 |
| Google Gemini | Google | Gemini 系列 |
| Groq | OpenAI | Llama，极速 |
| OpenRouter | OpenAI | 一站式多模型 |

## 部署注意

- API Key 不提交到 GitHub，使用环境变量或私有 config.json
- 生产环境请修改 `server.py` 中的 CORS 配置
- 话题审核过滤适合公开部署场景

## License

MIT
