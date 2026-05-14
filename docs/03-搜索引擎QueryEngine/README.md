# QueryEngine — 国内外新闻网页搜索 Agent

## 文件位置
- `QueryEngine/agent.py` (20KB) — Agent 主逻辑
- `QueryEngine/llms/` — LLM 接口封装
- `QueryEngine/nodes/` — 处理节点
- `QueryEngine/tools/` — 搜索工具集
- `QueryEngine/state/` — 状态管理
- `QueryEngine/prompts/` — 提示词模板
- `QueryEngine/utils/` — 工具函数

## 功能定位

**国内外新闻广度搜索 Agent**，负责搜索互联网上关于分析目标的最新新闻、文章和公开信息。

## 推荐模型
- **DeepSeek Chat**（官方推荐）
- API 申请：https://platform.deepseek.com/

## 搜索工具

支持两种搜索服务，通过配置文件切换：

| 工具 | 类型 | 申请地址 |
|------|------|---------|
| **BochaAPI** | AI 搜索 | https://open.bochaai.com/ |
| **AnspireAPI** | AI 搜索 | https://open.anspire.cn/ |

## 工作流程

```
用户问题
    │
    ▼
┌──────────────────┐
│  搜索策略制定     │ ← LLM 决策：关键词/平台/时间范围
└────────┬─────────┘
         ▼
┌──────────────────┐
│  并行搜索        │ ← 爬取多源新闻
│  (多关键词+多平台)│
└────────┬─────────┘
         ▼
┌──────────────────┐
│  内容格式化      │ ← 清洗、去重、结构化
└────────┬─────────┘
         ▼
┌──────────────────┐
│  多轮反思总结    │ ← 反思→补充搜索→再总结（循环）
│  (Reflection)    │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  最终输出        │ → 结构化搜索结果 + 分析摘要
└──────────────────┘
```

## 核心节点 (Nodes)

| 节点 | 功能 |
|------|------|
| `FirstSearchNode` | 首次搜索执行节点 |
| `FirstSummaryNode` | 首次结果总结节点 |
| `ReflectionNode` | 反思节点：分析已获取内容，找出缺失信息 |
| `ReflectionSummaryNode` | 反思总结节点 |

## 与其他引擎的协作

1. QueryAgent 与 MediaAgent、InsightAgent **并行启动**
2. 三个 Agent 各自独立完成初步分析
3. 在 ForumEngine 的论坛机制中，QueryAgent 负责提供**外部公开信息**视角
4. 最终所有结果汇总到 ReportEngine 用于报告生成
