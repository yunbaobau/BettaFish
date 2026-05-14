# InsightEngine — 深度洞察 Agent（本地数据库挖掘）

## 文件位置
- `InsightEngine/agent.py` (41KB) — Agent 主逻辑（最大的 Agent）
- `InsightEngine/llms/` — LLM 接口封装
- `InsightEngine/nodes/` — 处理节点
- `InsightEngine/tools/` — 数据库查询和分析工具集
- `InsightEngine/state/` — 状态管理
- `InsightEngine/prompts/` — 提示词模板
- `InsightEngine/utils/` — 工具函数

## 功能定位

**私有舆情数据库深度挖掘 Agent**，负责对本地数据库中存储的已采集内容进行深度分析：
- 分析历史舆情趋势
- 跨平台话题关联挖掘
- 大规模评论情感分析
- 聚类发现热点话题

## 推荐模型
- **Kimi K2**（官方推荐）
- API 申请：https://platform.moonshot.cn/

## 核心工具集 (tools/)

### 1. 数据库查询工具 (`search.py`)
基于 MindSpider 爬虫存入数据库的数据，提供 5 种专用查询：

| 工具 | 功能 | 说明 |
|------|------|------|
| `search_hot_content` | 热榜内容 | 按加权热度算法综合排序（点赞×1 + 评论×5 + 分享×10 + 观看×0.1） |
| `search_topic_globally` | 全局话题搜索 | 跨所有平台搜索与话题相关的内容和评论 |
| `search_topic_by_date` | 按日期搜索 | 在指定历史日期范围内搜索话题 |
| `get_comments_for_topic` | 获取评论 | 抽取特定话题的公众评论数据 |
| `search_topic_on_platform` | 按平台搜索 | 在 B站/微博等 7 大平台上精确搜索 |

### 2. 关键词优化器 (`keyword_optimizer.py`)
使用 **Qwen3 小参数模型** 对搜索关键词进行优化：
- 同义词扩展
- 语义理解优化
- 多语言关键词生成

### 3. 情感分析器 (`sentiment_analyzer.py`)
集成多语言情感分析模型（22种语言支持）。

## 核心处理节点

| 节点 | 功能 |
|------|------|
| `FirstSearchNode` | 首次搜索：从数据库检索相关内容 |
| `FirstSummaryNode` | 首次总结：对搜索结果进行归纳 |
| `ReflectionNode` | 反思：分析已有信息，找出盲点和不足 |
| `ReflectionSummaryNode` | 反思总结：对补充搜索的结果进行总结 |
| `ReportFormattingNode` | 报告格式化：将分析结果整理为结构化格式 |

## 聚类分析

使用 Sentence-Transformers 进行语义聚类：
```python
# 多语言语义模型
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
# KMeans 聚类
clusters = KMeans(n_clusters=k)
```

作用：从海量评论中抽取**典型代表性样本**，避免 LLM 处理时信息过载。

## 数据层 (utils/)

### 数据库访问 (`utils/db.py`)
- SQLAlchemy 异步引擎
- 只读查询封装（安全）
- 支持 MySQL / PostgreSQL

### 文本处理 (`utils/text_processing.py`)
- 清洗 HTML 标签
- 去除噪音字符
- 文本截断与分段

## 工作流程

```
分析请求
    │
    ▼
┌──────────────────┐
│  关键词优化       │ ← Qwen3 模型优化搜索词
└────────┬─────────┘
         ▼
┌──────────────────┐
│  数据库检索       │ ← 5 种查询工具按需调用
└────────┬─────────┘
         ▼
┌──────────────────┐
│  情感分析         │ ← 多语言情感模型批量分析
└────────┬─────────┘
         ▼
┌──────────────────┐
│  聚类采样         │ ← 语义聚类降维
└────────┬─────────┘
         ▼
┌──────────────────┐
│  LLM 深度分析     │ ← Kimi 模型综合分析
│  (多轮反思)        │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  结构化输出       │ → 分析结果 + 情感趋势 + 话题聚类
└──────────────────┘
```
