# AI Cockpit — 多平台网页 AI 协同指挥台

基于 Camoufox（反检测 Firefox）的多账号 AI 网页版统一管理工具。

## 快速开始

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

## API 文档

启动后端后访问 http://localhost:8080/docs

## 项目结构

详见 PLAN.md
