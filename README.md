# AI Cockpit — 多平台网页 AI 协同指挥台

基于 Camoufox（反检测 Firefox）的多账号 AI 网页版统一管理工具。

核心理念：**不是转 API，而是让多个 AI 浏览器实例互相配合、协同工作。**

## ✨ 核心特性

- 🖥️ **可视化浏览器墙** — 一个 WebUI 看到所有浏览器实时画面
- 🤖 **多账号管理** — 每个账号独立 Profile，登录态持久化
- 🔗 **AI 协同工作流** — 流水线、讨论组、审核链、辩论赛
- 🎮 **人随时可介入** — 有头模式 + WebUI，手动操作无障碍
- 📊 **状态监控** — 在线/掉线/验证码/额度，一眼看清
- 🔍 **多平台对比** — 同一 prompt 并发发送，结果并排对比
- 🔌 **适配器热加载** — 新平台只需写一个适配器文件

## 🤖 支持平台

| 平台 | 适配器 | 状态 |
|---|---|---|
| ChatGPT | `chatgpt.py` | ✅ 完整 |
| DeepSeek | `deepseek.py` | ✅ 完整 |
| Gemini | `gemini.py` | ✅ 完整 |
| 豆包 | `doubao.py` | ✅ 完整 |
| LMArena | `lmarena.py` | ✅ 完整 |

> 新平台只需在 `backend/app/browser/adapters/` 目录下添加一个 Python 文件，实现 `BaseAdapter` 接口即可。

## 🔗 工作流模式

| 模式 | 说明 | 适用场景 |
|---|---|---|
| ⚡ Pipeline | A→B→C 链式执行 | 文章生成、翻译校对 |
| 💬 Roundtable | 多 AI 圆桌讨论 | 多角度分析、头脑风暴 |
| 🔄 Review Loop | 写→审→改→审循环 | 代码审核、质量把关 |
| ⚔️ Debate | 正方 vs 反方 + 评委 | 观点碰撞、决策辅助 |

## 🚀 快速开始

### 后端

```bash
cd backend
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

### Docker

```bash
docker-compose up -d
```

## 📡 API

启动后端后访问 http://localhost:8080/docs

### 主要端点

```
# 账号管理
POST   /api/accounts                    # 添加账号
GET    /api/accounts                    # 账号列表

# 实例控制
POST   /api/instances/{id}/start        # 启动浏览器
POST   /api/instances/{id}/stop         # 停止浏览器
POST   /api/instances/{id}/chat         # 发消息并等回复
POST   /api/instances/{id}/login        # 触发登录流程

# 工作流
GET    /api/workflows                   # 工作流列表
POST   /api/workflows                   # 创建工作流
POST   /api/workflows/{id}/run          # 执行工作流
POST   /api/workflows/run/{rid}/pause   # 暂停
POST   /api/workflows/run/{rid}/resume  # 恢复
POST   /api/workflows/run/{rid}/abort   # 终止

# 适配器
GET    /api/adapters                    # 适配器列表
POST   /api/adapters/reload             # 热加载适配器

# WebSocket
WS     /ws/instances/{id}/screen        # 截图流
WS     /ws/instances/{id}/chat          # 实时对话
WS     /ws/global                       # 全局状态
```

## 🏗️ 项目结构

```
ai-cockpit/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理
│   │   ├── models.py            # 数据模型
│   │   ├── database.py          # SQLite
│   │   ├── browser/
│   │   │   ├── pool.py          # 实例池
│   │   │   ├── instance.py      # 实例封装
│   │   │   └── adapters/        # 平台适配器
│   │   ├── api/                 # REST + WebSocket
│   │   ├── workflow/
│   │   │   ├── bus.py           # 消息总线
│   │   │   ├── engine.py        # 工作流引擎
│   │   │   ├── runner.py        # 执行器
│   │   │   └── templates.py     # 预置模板
│   │   └── utils/
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── App.tsx              # 路由 + 侧边栏
│       ├── pages/
│       │   ├── Dashboard.tsx    # 总览仪表盘
│       │   ├── Accounts.tsx     # 账号管理
│       │   ├── LiveView.tsx     # 实时视图
│       │   ├── WorkflowEditor.tsx  # React Flow 编辑器
│       │   └── CompareView.tsx  # 多平台对比
│       ├── hooks/               # WebSocket hooks
│       ├── stores/              # Zustand 状态
│       └── lib/api.ts           # API 客户端
├── config.yaml
└── docker-compose.yml
```

## ⚙️ 配置

```yaml
# config.yaml
server:
  host: "0.0.0.0"
  port: 8080

browser:
  max_concurrent: 5
  screenshot_fps: 1
  headless: false
```

## 📋 硬件要求

| 资源 | 最低 | 推荐 |
|---|---|---|
| CPU | 2 核 | 4 核+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘 | 10 GB | 20 GB+ |

> 每个 Camoufox 实例约 200-400MB 内存。

## 📄 License

MIT
