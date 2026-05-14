# ReportEngine — 智能报告生成 Agent

## 文件位置
- `ReportEngine/agent.py` (66KB) — **最大的文件**，总调度器
- `ReportEngine/flask_interface.py` (51KB) — Flask/SSE 入口
- `ReportEngine/core/` — 核心功能
- `ReportEngine/ir/` — 报告中间表示（IR）
- `ReportEngine/nodes/` — 全流程推理节点
- `ReportEngine/renderers/` — 渲染器
- `ReportEngine/report_template/` — Markdown 模板库
- `ReportEngine/state/` — 状态管理
- `ReportEngine/prompts/` — 提示词库

## 功能定位

**多轮报告生成 Agent**，是整个系统的"最后一公里"：
- 收集所有 Agent 的分析结果
- 动态选择报告模板
- 多轮迭代生成报告内容
- 渲染为交互式 HTML / PDF

## 推荐模型
- **Gemini 2.5 Pro**（官方推荐）
- 推荐中转厂商：https://aihubmix.com/

## 整体流程

```
Flask请求
    │
    ▼
┌────────────────────────────┐
│  flask_interface.py        │
│  (任务排队 + SSE 流式推送)  │
└───────────┬────────────────┘
            ▼
┌────────────────────────────┐
│  agent.py (总调度器)        │
│  模板选择 → 布局 → 篇幅     │
│       → 章节 → 渲染        │
└───────────┬────────────────┘
            ▼
     ┌──────┴──────┐
     │              │
     ▼              ▼
┌─────────┐  ┌──────────┐
│   IR     │  │ Renderers│
│ 中间表示  │  │ HTML/PDF │
└─────────┘  └──────────┘
```

## 核心子系统

### 1. 模板系统 (`report_template/`)
Markdown 模板库，如 `企业品牌声誉分析报告.md`，定义了报告的骨架结构。

### 2. 核心引擎 (`core/`)

| 模块 | 功能 |
|------|------|
| `template_parser.py` | Markdown 模板切片与 slug 生成 |
| `chapter_storage.py` | 章节 run 目录、manifest 与 raw 流写入 |
| `stitcher.py` | Document IR 装订器，补齐锚点/元数据 |

### 3. IR 中间表示 (`ir/`)

- **`schema.py`** — 块/标记 Schema 常量定义
- **`validator.py`** — 章节 JSON 结构校验器

IR 将报告抽象为 **块（Block）+ 标记（Tag）+ 元数据（Metadata）** 的结构化数据，实现内容与渲染分离。

### 4. 推理节点 (`nodes/`)

| 节点 | 功能 |
|------|------|
| `base_node.py` | 节点基类 + 日志/状态钩子 |
| `template_selection_node.py` | 模板候选收集与 LLM 筛选 |
| `document_layout_node.py` | 标题/目录/主题设计 |
| `word_budget_node.py` | 篇幅规划与章节指令生成 |
| `chapter_generation_node.py` | 章节级 JSON 生成 + 校验 |

### 5. 渲染器 (`renderers/`)

| 渲染器 | 功能 |
|--------|------|
| `html_renderer.py` | Document IR → 交互式 HTML |
| `pdf_renderer.py` | HTML → PDF 导出（WeasyPrint） |
| `pdf_layout_optimizer.py` | PDF 布局优化 |
| `chart_to_svg.py` | 图表转 SVG |

### 6. SSE 接口 (`flask_interface.py`)
- Flask Blueprint 注册
- 任务排队管理
- 流式事件推送（实时进度展示）

## 报告生成流程

```
Step 1: 模板选择
  ├─ 从模板库收集候选模板
  ├─ LLM 根据分析内容筛选最合适的模板
  └─ 确定报告基调

Step 2: 布局设计
  ├─ 确定标题和目录结构
  ├─ 设计主题风格
  └─ 规划视觉元素

Step 3: 篇幅规划
  ├─ 估算总字数
  ├─ 各章节字数分配
  └─ 生成章节级写作指令

Step 4: 章节生成（多轮）
  ├─ 逐章节生成 JSON 内容
  ├─ 即时校验结构完整性
  └─ 补充缺失信息

Step 5: IR 装订
  ├─ 补齐锚点引用
  ├─ 添加元数据
  └─ 生成完整 Document IR

Step 6: 渲染输出
  ├─ 交互式 HTML（主输出）
  └─ PDF 导出（可选）
```

## 质量保证

- **章节校验**：每一章生成后进行 JSON schema 校验
- **图表校验**：`chart_validator.py` 确保图表数据正确
- **依赖检查**：`dependency_check.py` 检查渲染依赖
