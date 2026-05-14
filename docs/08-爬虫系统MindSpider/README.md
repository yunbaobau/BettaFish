# MindSpider — AI 爬虫系统

## 文件位置
- `MindSpider/main.py` (23KB) — 爬虫主程序入口
- `MindSpider/config.py` (2KB) — 爬虫配置
- `MindSpider/BroadTopicExtraction/` — 广泛话题提取模块
- `MindSpider/DeepSentimentCrawling/` — 深层情感爬取模块
- `MindSpider/schema/` — 数据库 schema

## 功能定位

**社交媒体数据采集层**，负责：
- 7x24 小时不间断采集 10+ 社交媒体平台数据
- 广泛话题发现与提取
- 深层评论数据爬取
- 数据入库供 InsightEngine 分析

## 数据采集范围

覆盖国内外主流社交媒体平台（10+ 平台）：
- 微博
- 小红书
- 抖音
- 快手
- B站
- 知乎
- 头条
- Twitter/X
- 等...

## 两大核心模块

### 1. BroadTopicExtraction（广泛话题提取）
- 发现当前热点话题
- 提取话题关键词
- 识别新兴趋势
- 生成话题画像

### 2. DeepSentimentCrawling（深层情感爬取）
- 深入爬取评论区内容
- 获取海量用户真实反馈
- 为情感分析提供原始数据
- 支持多级评论嵌套

## 技术实现

### 数据库存储

支持 MySQL / PostgreSQL：
```python
# 异步数据库引擎
from sqlalchemy.ext.asyncio import create_async_engine

# MySQL
f"mysql+asyncmy://{user}:{password}@{host}:{port}/{db}"
# PostgreSQL
f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
```

### 数据模型

数据库 schema 位于 `MindSpider/schema/`，主要表结构：
- **platforms** — 平台信息
- **topics** — 话题
- **contents** — 内容（帖子/文章/视频）
- **comments** — 评论
- **sentiments** — 情感分析结果
- **hot_scores** — 热度评分

### 配置要求

```python
required_configs = [
    'DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME',
    'MINDSPIDER_API_KEY', 'MINDSPIDER_BASE_URL', 'MINDSPIDER_MODEL_NAME'
]
```

## 与 InsightEngine 的关系

```
MindSpider                          InsightEngine
（数据采集层）                         （分析层）

社交媒体 ──→ 爬虫采集 ──→ 数据库 ──→ 数据库查询工具
                                        │
                                    LLM深度分析
                                        │
                                    输出分析结果
```

- MindSpider 负责**写**数据（爬取→入库）
- InsightEngine 负责**读**数据（查库→分析）
- 两者通过数据库解耦

## 运行方式

```bash
# 命令行启动
python MindSpider/main.py

# 通过 Flask 主应用集成
from MindSpider.main import MindSpider
spider = MindSpider()
spider.check_config()
spider.check_database_connection()

# 作为独立爬虫运行
python MindSpider/main.py --mode broad_topic  # 仅话题提取
python MindSpider/main.py --mode deep_sentiment  # 仅情感爬取
```
