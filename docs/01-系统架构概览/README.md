# BettaFish "微舆" 系统架构概览

## 项目定位

"微舆" 是一个 **多智能体舆情分析系统**，从零实现。用户只需像聊天一样提出分析需求，系统自动完成：
- 国内外 30+ 主流社媒的数据采集
- 数百万条大众评论分析
- 多维度舆情研判
- 交互式 HTML 报告生成

> 名称由来：BettaFish（斗鱼）——体型小但非常好斗、漂亮，象征"小而强大，不畏挑战"

## 整体架构

```
用户提问
    │
    ▼
┌─────────────────────────────────────────┐
│           Flask 主应用 (app.py)           │
│  接收请求 → 并行启动 3 个 Agent → 等待完成 │
└────┬─────────┬──────────┬────────────────┘
     │         │          │
     ▼         ▼          ▼
┌─────────┐ ┌────────┐ ┌──────────┐
│QueryAgent│ │MediaAgent││InsightAgent│
│(网页搜索)│ │(多模态)  ││(数据库挖掘)│
└────┬────┘ └───┬────┘ └────┬─────┘
     │          │           │
     └──────────┼───────────┘
                ▼
     ┌──────────────────┐
     │  ForumEngine     │
     │  (论坛协作机制)   │
     │  Agent辩论+融合  │
     └────────┬─────────┘
              ▼
     ┌──────────────────┐
     │  ReportEngine    │
     │  (报告生成引擎)   │
     │  IR中间表示→渲染  │
     └──────────────────┘
```

## 六大核心引擎

| 模块 | 功能 | 核心文件 |
|------|------|---------|
| **QueryEngine** | 国内外新闻网页搜索 Agent | `agent.py` (19KB) |
| **MediaEngine** | 多模态内容理解（视频/图片） Agent | `agent.py` (20KB) |
| **InsightEngine** | 本地数据库深度挖掘 Agent | `agent.py` (41KB) |
| **ForumEngine** | Agent "论坛" 协作机制 | `monitor.py` (39KB) + `llm_host.py` |
| **ReportEngine** | 多轮报告生成 Agent | `agent.py` (66KB) + `flask_interface.py` (51KB) |
| **MindSpider** | AI爬虫系统（数据采集层） | `main.py` (23KB) |

## 辅件模块

| 模块 | 功能 |
|------|------|
| **SentimentAnalysisModel** | 5种情感分析/主题检测模型 |
| **SingleEngineApp** | 3个独立 Streamlit 应用（单引擎测试） |
| **utils/** | 工具函数（论坛阅读器、重试助手等） |
| **static/** | 静态资源（图片、示例报告） |
| **templates/** | Flask 前端模板 (index.html 5.4MB) |

## 一次完整分析流程

```
步骤1: 用户提问 → Flask主应用接收查询
步骤2: 并行启动 → QueryAgent + MediaAgent + InsightAgent 同时开始工作
步骤3: 初步分析 → 各Agent使用专属工具进行概览搜索
步骤4: 策略制定 → 基于初步结果制定分块研究策略
步骤5-N: 循环阶段 → 论坛协作 + 深度研究（多轮循环）
  ├─ 深度研究：各Agent基于论坛主持人引导进行专项搜索
  ├─ 论坛协作：ForumEngine监控Agent发言并生成主持人引导
  └─ 交流融合：各Agent根据讨论调整研究方向
步骤N+1: 结果整合 → ReportAgent收集所有分析结果和论坛内容
步骤N+2: IR中间表示 → 动态选择模板，多轮生成元数据
步骤N+3: 报告生成 → 分块质量检测，基于IR渲染成交互式HTML报告
```

## 关键技术栈

- **后端框架**: Flask + Flask-SocketIO
- **数据库**: MySQL/PostgreSQL (SQLAlchemy 异步引擎)
- **LLM集成**: OpenAI兼容接口 (支持 Kimi / Gemini / DeepSeek / Qwen 等)
- **爬虫**: 基于 Playwright 的 AI 爬虫
- **情感分析**: 多语言情感模型 + 微调 BERT
- **向量聚类**: Sentence-Transformers + KMeans
- **报告渲染**: HTML (交互式) + PDF (WeasyPrint)
- **部署**: Docker + docker-compose
