# ForumEngine — Agent"论坛"协作机制

## 文件位置
- `ForumEngine/monitor.py` (39KB) — 日志监控和论坛管理核心
- `ForumEngine/llm_host.py` (11KB) — 论坛主持人 LLM 模块
- `utils/forum_reader.py` (5KB) — 论坛阅读工具

## 功能定位

**多 Agent 协作核心**，这是 BettaFish 最具创新性的模块：
- 实时监控 3 个 Agent 的日志输出
- 检测 Agent 的关键发现（SummaryNode 输出）
- 触发"论坛主持人"生成引导发言
- 促进 Agent 间的思想碰撞与融合

## 为什么需要"论坛"？

单个 LLM 存在思维局限，简单的信息汇总会产生"同质化"结论。ForumEngine 模拟**学术研讨会**：
- 每个 Agent 是不同的"专家学者"
- 论坛主持人引导讨论方向
- Agent 之间可以互相"阅读"对方的发现
- 通过多轮辩论达成更高质量的集体结论

## 核心组件

### 1. LogMonitor (`monitor.py`)

基于文件变化的智能日志监控器：

```python
class LogMonitor:
    monitored_logs = {
        'insight': 'logs/insight.log',
        'media': 'logs/media.log',
        'query': 'logs/query.log'
    }
```

**工作机制：**
1. 实时监控 3 个 Agent 的日志文件
2. 用正则表达式匹配 SummaryNode 的输出 JSON
3. 将 Agent 的发现存入 `agent_speeches_buffer`
4. 每收集 5 条发言触发一次主持人发言
5. 将论坛讨论写入 `forum.log`

**关键参数：**
| 参数 | 值 | 说明 |
|------|-----|------|
| `host_speech_threshold` | 5 | 每5条agent发言触发一次主持人 |
| `target_node_patterns` | 6种模式 | 匹配SummaryNode输出 |

### 2. ForumHost (`llm_host.py`)

论坛主持人，使用独立的 LLM（推荐 Qwen3）：

```python
class ForumHost:
    def __init__(self, api_key, base_url, model_name):
        # 使用硅基流动的 Qwen3 模型
        self.client = OpenAI(api_key=..., base_url=...)
```

**主持人职责：**
1. 阅读所有 Agent 的最新发现
2. 识别不同 Agent 的共识和分歧
3. 指出被忽略的角度和盲点
4. 引导下一轮研究的方向
5. 避免重复已有讨论

### 3. 论坛阅读器 (`utils/forum_reader.py`)

供 Agent 使用的工具，让 Agent 可以"看到"论坛中其他 Agent 的发言：
- 读取 `forum.log` 中的讨论记录
- 获取最新的主持人引导
- 了解其他 Agent 的研究方向

## 论坛协作流程

```
Agent1(Insight)  Agent2(Media)  Agent3(Query)
    │               │               │
    ▼               ▼               ▼
  日志输出         日志输出         日志输出
    │               │               │
    └───────────────┼───────────────┘
                    ▼
        ┌─────────────────────┐
        │   LogMonitor        │
        │   (实时监控日志)      │
        │   发现SummaryNode   │
        └──────────┬──────────┘
                   ▼
        ┌─────────────────────┐
        │   agent_speeches    │
        │   (收集到5条发言)    │
        └──────────┬──────────┘
                   ▼
        ┌─────────────────────┐
        │   ForumHost         │
        │   (主持人发言)       │
        │   → 引导下一轮方向    │
        └──────────┬──────────┘
                   ▼
        ┌─────────────────────┐
        │   Agent们读到引导    │
        │   调整研究方向       │
        │   继续深度分析       │
        └──────────┬──────────┘
                   │
         (回到顶部，进入下一轮)
                   │
                   ▼
        ┌─────────────────────┐
        │  达到最大反思轮数    │
        │  或主持人认为足够    │
        └─────────────────────┘
```

## 关键设计要点

1. **异步非阻塞**：监控线程不阻塞 Agent 运行
2. **JSON 解析**：从日志文本中提取结构化的 Agent 发言
3. **去重机制**：`ForumHost` 跟踪已处理过的内容，避免重复
4. **阈值控制**：通过 `MAX_REFLECTIONS` 控制反思轮数上限
5. **错误恢复**：主持人 LLM 调用失败时以纯监控模式继续运行
