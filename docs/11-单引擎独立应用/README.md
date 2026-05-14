# SingleEngineApp — 单引擎独立 Streamlit 应用

## 文件位置
- `SingleEngineApp/insight_engine_streamlit_app.py` (8KB)
- `SingleEngineApp/media_engine_streamlit_app.py` (11KB)
- `SingleEngineApp/query_engine_streamlit_app.py` (8KB)

## 功能定位

**独立运行每个 Agent 的测试工具**，使用 Streamlit 构建 Web UI：
- 在不启动 Flask 主应用的情况下，单独测试每个引擎
- 快速验证某个 Agent 的功能和效果
- 方便开发和调试

## 三个独立应用

### 1. InsightEngine Streamlit App
```bash
streamlit run SingleEngineApp/insight_engine_streamlit_app.py
```
- 直接连接数据库
- 输入分析需求，调用 DeepSearchAgent
- 展示深度分析结果

### 2. MediaEngine Streamlit App
```bash
streamlit run SingleEngineApp/media_engine_streamlit_app.py
```
- 输入搜索关键词或图片/视频链接
- 调用 MediaAgent 进行多模态分析
- 展示多模态理解结果

### 3. QueryEngine Streamlit App
```bash
streamlit run SingleEngineApp/query_engine_streamlit_app.py
```
- 输入搜索查询
- 调用 QueryAgent 进行全网搜索
- 展示搜索和分析结果

## 适用场景

| 场景 | 使用应用 | 理由 |
|------|---------|------|
| 数据库分析测试 | InsightEngine App | 直接查库，无需爬虫 |
| 多模态能力测试 | MediaEngine App | 独立验证图文理解 |
| 搜索质量测试 | QueryEngine App | 评估搜索工具效果 |
| 快速原型验证 | 任意 Streamlit App | 轻量级启动 |

## 技术特点

- 使用 **Streamlit** 框架，比 Flask 前端开发更快
- 每个 App 都是独立的 Python 脚本
- 直接调用对应 Engine 的 Agent 类
- 支持实时输出显示

## 开发学习价值

对于想理解单个 Agent 工作流程的开发者，Streamlit App 是很好的入口点：
1. 代码更简短（8-11KB vs Agent 的 20-66KB）
2. 无复杂的前后端通信
3. 清晰的输入→处理→输出流程
4. 可单独调试和断点追踪

## 报告存放

每个 App 运行后生成的报告会存放在各自的报告目录：
- `insight_engine_streamlit_reports/`
- `media_engine_streamlit_reports/`
- `query_engine_streamlit_reports/`
