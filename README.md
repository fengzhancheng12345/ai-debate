# 🎙️ AI Debate System — 智能辩论平台

> *输入一个话题，多个 AI 角色展开正反辩论，实时抓取真实数据，投票统计立场差异。*

[![GitHub stars](https://img.shields.io/github/stars/fengzhancheng12345/ai-debate?style=flat-square&logo=github)](https://github.com/fengzhancheng12345/ai-debate)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-green?style=flat-square&logo=python)](requirements.txt)

---

## ✨ 核心特性

### 🤖 多智能体实时辩论
每次辩论由 2 组 × 3 个 AI 角色组成，每组 3 人分别从不同视角发表观点。通过 SSE 流式传输，辩论过程实时呈现在界面上，无需等待。

### 🔍 实时研究数据
辩论开始前，自动并行抓取 **真实免费数据源**，为 AI 提供事实支撑：

| 数据源 | 内容 | 所需 |
|--------|------|------|
| 🌐 Bing 搜索 | 网络搜索结果摘要 | 无需 Key |
| 📚 Wikipedia | 百科词条 | 无需 Key |
| 📈 FRED (美联储) | 美国经济宏观数据 | 无需 Key |
| 💹 Yahoo Finance | 股票/指数行情 | 无需 Key |
| 📑 arXiv | 学术论文摘要 | 无需 Key |
| 🔬 Semantic Scholar | 学术引用分析 | 无需 Key |
| 💻 GitHub | 开源项目信息 | 无需 Key |
| 📰 科技新闻 | 最新科技资讯 | 无需 Key |

### 🗳️ 投票与对比
- 每轮结束各 agent 投票（支持 / 反对 / 中立）
- 用户也可以投出自己的一票
- 辩论结束后，**人机投票对比**：显示你的立场与 AI 大多数的差异

### 📊 结构化报告导出
辩论完成后，一键导出 **Markdown** 或 **TXT** 格式的完整报告，包含所有轮次要点、AI 投票统计和主策划总结。

### 🎨 专业深色 UI
专为辩论场景设计的深色界面，带实时进度条、折叠式投票监控、智能滚动、引用来源高亮。

---

## 🏗️ 系统架构

```
用户输入话题
      │
      ▼
┌─────────────────────────────────────────┐
│          server.py (FastAPI)            │
│   • /api/debate/analyze  话题分析      │
│   • /api/debate/start    启动辩论       │
│   • /api/debate/{id}/stream  SSE流     │
│   • /api/config         API设置        │
└──────────────────┬────────────────────┘
                   │
       ┌──────────┴──────────┐
       ▼                      ▼
┌──────────────┐      ┌──────────────────┐
│ agents.py    │      │ researcher.py    │
│              │      │                  │
│ • 主策划     │      │ • 并行抓取 8 个来源│
│   (Planner)  │      │ • 智能选择数据源  │
│ • 辩论小组   │      │ • 按话题类型      │
│   (2组×3人) │      │   决定抓什么      │
│ • 轮次编排   │      │ • 免费数据源      │
│ • 投票收集   │      └──────────────────┘
│ • 最终总结   │
└──────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│   templates/debate.html (纯前端)         │
│   • SSE 事件处理                        │
│   • 实时 UI 更新                        │
│   • 投票统计                            │
│   • Markdown 渲染 / 图片 / 表格          │
│   • 引用来源徽章                        │
└─────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境要求
- Python 3.10+
- 无需数据库（会话存储在内存中）

### 1. 克隆项目
```bash
git clone https://github.com/fengzhancheng12345/ai-debate.git
cd ai-debate
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

> **提示**：研究模块依赖 `yfinance`（可选），用于财经数据。如需安装：
> ```bash
> pip install yfinance
> ```

### 3. 配置 API Key
**方式一：通过 UI（推荐）**
启动后访问 http://localhost:8098，点击右上角 ⚙️ 设置，输入你的 API Key。

**方式二：通过环境变量**
```bash
export MINIMAX_API_KEY="your_key_here"
export MINIMAX_MODEL="MiniMax-M2.7"
python start.py
```

### 4. 启动服务
```bash
python start.py
# 或直接
python server.py
```

访问 **http://localhost:8098** 即可使用。

---

## ⚙️ 支持的 API Provider

| Provider | 模型 | 特点 | API 格式 |
|----------|------|------|---------|
| 🔬 **MiniMax** | M2.7 / M2.5 | 中文优化，默认推荐 | Anthropic |
| 🔵 **DeepSeek** | V3 / R1 | 性价比高 | OpenAI |
| ⚡ **OpenAI** | GPT-4o / GPT-4o Mini | 最强模型 | OpenAI |
| 🧠 **Anthropic** | Claude 3.5 / 3.7 | 长上下文强 | Anthropic |
| 🌐 **Google** | Gemini 1.5 / 2.0 | Google 全家桶 | Google AI |
| ⚡ **Groq** | Llama / Mixtral | 免费高速 | OpenAI |
| 🌍 **OpenRouter** | 聚合 100+ 模型 | 按量付费 | OpenAI |

> API Key 仅存储在**浏览器本地**，不会上传到任何服务器。

---

## 📖 辩论流程详解

```
1️⃣  话题分析
     用户输入话题 → AI 分析需要哪些背景信息
     → 生成动态表单（收集用户资金/偏好/条件）

2️⃣  策划阶段
     主策划 LLM 根据话题设计辩论结构
     → 决定分组数量、角色类型、辩论角度

3️⃣  研究阶段
     并行抓取多个真实数据源（无 Key 需求）
     → 数据实时显示在界面上

4️⃣  多轮辩论
     每轮：
       • 各 agent 轮流发言（带引用来源）
       • 轮次结束显示「本轮要点摘要」
       • 用户可随时滚动查看历史

5️⃣  投票阶段
     每组内部投票：支持 / 反对 / 中立
     → 实时投票进度条

6️⃣  总结对比
     主策划综合所有观点，给出最终结论
     → 用户投票与人机投票对比
     → 导出 Markdown 报告
```

---

## 🎯 使用场景

| 场景 | 示例话题 |
|------|---------|
| **投资决策** | 现在是买特斯拉股票的好时机吗？ |
| **科技产品** | iPhone 16 值得升级吗？ |
| **政策讨论** | AI 监管应该更严格还是更宽松？ |
| **职业选择** | 现在是转行做 AI 的好时机吗？ |
| **消费决策** | 现在买电车合适还是买油车更划算？ |
| **学术争议** | Transformer 架构还能统治 AI 多少年？ |

---

## 📁 项目结构

```
ai-debate/
├── server.py            # FastAPI 服务器，API 路由，SSE 流
├── agents.py            # 辩论智能体编排，主策划，轮次管理
├── researcher.py         # 研究数据抓取层（8 个并行数据源）
├── store.py             # 内存会话存储（不落盘）
├── minimax.py           # MiniMax API 客户端封装
├── moderation.py        # 内容安全过滤
├── config.example.py    # 配置模板（复制为 config.py）
├── requirements.txt     # Python 依赖
├── start.py            # 启动入口
├── README.md           # 本文档
├── templates/
│   └── debate.html     # 完整单文件前端（HTML+CSS+JS）
```

---

## 🔧 高级配置

### 修改辩论轮数
在 `server.py` 或启动时传入参数，默认 2 轮：

```python
# agents.py 中修改
total_rounds=2  # 默认值
```

### 修改 Agent 数量限制
Planner 会自动设计分组，但受 `agents.py` 中的 `max_tokens` 和提示约束。硬限制：每组最多 3 人，最多 2 组。

### 接入其他数据源
在 `researcher.py` 中添加新的 `_fetch_xxx` 方法即可，自动被 `_plan_sources` 选中。

---

## 🛡️ 隐私说明

- **API Key**：存储在浏览器 `localStorage`，不经过服务器
- **会话数据**：存储在服务器内存（`store.py`），服务重启即丢失
- **辩论内容**：不保存、不上传、不共享
- **数据源**：全部为公开免费来源，无追踪、无登录要求

---

## 🎨 界面预览

```
┌─────────────────────────────────┬──────────────────┐
│  🎙️ AI 辩论系统                │ ⚠️ 未配置 | 📥 导出 │
├─────────────────────────────────┼──────────────────┤
│                                 │ 📝 发起辩论        │
│  [实时投票监控 - 可折叠]         │ [话题输入框]       │
│  ████████████░░░░  支持 62%    │ [开始分析]        │
│  ████░░░░░░░░░░░  反对 25%    │                  │
│  ██░░░░░░░░░░░░░  中立 13%    │ 📡 实时进度       │
│                                 │ ● 策划阶段        │
│  ─────────────────────────────  │ ● 研究阶段        │
│  🔄 第 2 轮 — 正方立论           │ ● 辩论进行中      │
│                                 │                  │
│  ┌─ 正方立论组 ──────────────┐  │ 🗳️ 你的立场       │
│  │ 🔬 研究员 | 第2轮 [spinner] │ │ [👍支持][👎反对]  │
│  │ 内容：xxx... [来源: FRED]   │ │ [🤔中立]         │
│  │                               │ │                  │
│  │ 🤔 质疑者 | 第2轮            │ │ [提交我的投票]    │
│  │ 内容：xxx... [来源: arXiv]  │ │                  │
│  └────────────────────────────┘  │                  │
│                                 │                  │
│  📋 第2轮要点                    │                  │
│  [本轮摘要内容...]               │                  │
└─────────────────────────────────┴──────────────────┘
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！如果是新功能，建议先开 Issue 讨论。

## 📄 License

MIT License — 可自由使用、修改和分发。
