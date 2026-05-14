# SentimentAnalysisModel — 情感分析与主题检测模型

## 文件位置
- `SentimentAnalysisModel/BertTopicDetection_Finetuned/` — 微调 BERT 主题检测
- `SentimentAnalysisModel/WeiboMultilingualSentiment/` — 多语言情感分析（22种语言）
- `SentimentAnalysisModel/WeiboSentiment_Finetuned/` — 微调微博情感模型
- `SentimentAnalysisModel/WeiboSentiment_MachineLearning/` — 传统 ML 情感模型
- `SentimentAnalysisModel/WeiboSentiment_SmallQwen/` — 小参数 Qwen 情感模型

## 功能定位

**5 种模型组合**，覆盖从传统机器学习到深度学习的多种情感分析/主题检测方案。

## 模型清单

### 1. WeiboMultilingualSentiment（主推模型）
- **能力**：支持 22 种语言的情感分析
- **应用**：作为 InsightEngine 的默认情感分析器
- **集成方式**：
  ```python
  from InsightEngine.tools import multilingual_sentiment_analyzer
  result = multilingual_sentiment_analyzer.analyze(text)
  ```

### 2. WeiboSentiment_Finetuned
- **能力**：针对微博内容微调的情感模型
- **优势**：在中文社交媒体文本上准确率更高
- **适用场景**：纯中文微博语料分析

### 3. WeiboSentiment_SmallQwen
- **能力**：基于小参数 Qwen 模型的情感分析
- **优势**：部署成本低，推理速度快
- **适用场景**：对实时性要求高的场景

### 4. BertTopicDetection_Finetuned
- **能力**：基于 BERT 微调的主题检测模型
- **功能**：识别文本所属的话题类别
- **应用**：话题聚类和热点发现

### 5. WeiboSentiment_MachineLearning
- **能力**：传统机器学习情感分类（如 SVM、朴素贝叶斯等）
- **优势**：无需 GPU，部署最简单
- **适用场景**：资源受限环境

## 模型选型建议

| 场景 | 推荐模型 | 理由 |
|------|---------|------|
| 生产环境（多语言） | WeiboMultilingualSentiment | 支持22种语言，通用性强 |
| 微博专用 | WeiboSentiment_Finetuned | 中文社交媒体优化 |
| 实时/高并发 | WeiboSentiment_SmallQwen | 速度快、成本低 |
| 主题发现 | BertTopicDetection_Finetuned | 专为主题检测设计 |
| 无 GPU 部署 | WeiboSentiment_MachineLearning | 无需深度学习依赖 |

## 在系统中的集成

### 直接集成（InsightEngine）

```python
# InsightEngine 初始化时自动加载
self.sentiment_analyzer = multilingual_sentiment_analyzer

# 在深度分析中使用
sentiment_result = self.sentiment_analyzer.analyze(comment_text)
```

### 间接集成（通过数据库）

MindSpider 爬取数据时预处理情感标签，存入数据库，InsightEngine 查询时直接获取：
```
爬虫采集 → 情感分析 → 入库 → InsightEngine 查询 → 报告
```
