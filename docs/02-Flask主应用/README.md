# Flask 主应用 — 系统入口与调度中心

## 文件位置
- `app.py` (50KB) — 主应用
- `config.py` (9KB) — Pydantic 配置管理
- `templates/index.html` (5.4MB) — 前端页面

## 核心职责

Flask 主应用是系统的**总调度器**，负责：
1. 接收用户分析请求
2. 并行启动 QueryAgent / MediaAgent / InsightAgent
3. 监听各 Agent 的处理进度（通过日志文件）
4. 触发 ForumEngine 的论坛协作机制
5. 最后调用 ReportEngine 生成最终报告
6. 通过 SSE (Server-Sent Events) 实时推送进度给前端

## 关键架构设计

### 1. 蓝图注册
```python
# ReportEngine 以 Flask Blueprint 形式注册
app.register_blueprint(report_bp, url_prefix='/api/report')
```

### 2. 配置热加载
```python
# 支持运行时动态重新加载配置
from config import reload_settings, settings
reload_settings()  # 从 .env 文件重新读取配置
```

### 3. SSE 实时推送
使用 Flask-SocketIO 实现前端进度推送，支持客户端主动断开保护：
```python
# eventlet 连接中断安全防护
_patch_eventlet_disconnect_logging()
```

### 4. ReportEngine 集成
- 通过 `flask_interface.py` 集成
- 管理任务排队与流式事件
- 支持多任务并发处理

## 配置管理 (config.py)

使用 **pydantic-settings** 管理全局配置，支持：
- `.env` 文件自动加载
- 环境变量覆盖
- 运行时 `reload_settings()` 热加载

### 配置分类

| 类别 | 配置项 | 说明 |
|------|--------|------|
| Flask服务器 | HOST, PORT | 默认 0.0.0.0:5000 |
| 数据库 | DB_DIALECT, DB_HOST, DB_PORT ... | 支持 MySQL / PostgreSQL |
| Insight Agent | INSIGHT_ENGINE_API_KEY/BASE_URL/MODEL_NAME | 推荐 Kimi-k2 |
| Media Agent | MEDIA_ENGINE_API_KEY/BASE_URL/MODEL_NAME | 推荐 Gemini 2.5 Pro |
| Query Agent | QUERY_ENGINE_API_KEY/BASE_URL/MODEL_NAME | 推荐 DeepSeek |
| Report Agent | REPORT_ENGINE_API_KEY/BASE_URL/MODEL_NAME | 推荐 Gemini 2.5 Pro |
| MindSpider | MINDSPIDER_API_KEY/BASE_URL/MODEL_NAME | 推荐 DeepSeek |
| Forum Host | FORUM_HOST_API_KEY/BASE_URL/MODEL_NAME | 推荐 Qwen3 |
| 搜索工具 | TAVILY_API_KEY, SEARCH_TOOL_TYPE | 支持 Bocha / Anspire |
| 搜索参数 | DEFAULT_SEARCH_xxx | 各类搜索限制参数 |

## 启动流程

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 2. 直接启动
python app.py

# 3. 或使用 Docker
docker-compose up
```

## 前端界面

`templates/index.html` 是一个单页应用（5.4MB），包含：
- 用户输入框（类似聊天界面）
- 进度展示面板
- 实时日志输出
- 最终报告展示区域
