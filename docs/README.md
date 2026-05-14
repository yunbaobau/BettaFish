# BettaFish "微舆" 系统学习文档

> 基于 [BettaFish](https://github.com/666ghj/BettaFish) v1.2.1 源码分析
> 生成日期：2026-05-13

## 文档目录

| # | 文档 | 内容 | 关键文件大小 |
|---|------|------|-------------|
| 01 | [系统架构概览](./01-系统架构概览/README.md) | 整体架构、六大引擎、分析流程 | - |
| 02 | [Flask主应用与配置](./02-Flask主应用/README.md) | 启动流程、配置管理、前端集成 | app.py 50KB |
| 03 | [QueryEngine 搜索引擎](./03-搜索引擎QueryEngine/README.md) | 网页搜索Agent、搜索工具、反思机制 | agent.py 20KB |
| 04 | [MediaEngine 多模态引擎](./04-多模态引擎MediaEngine/README.md) | 视频/图片理解、多模态搜索 | agent.py 20KB |
| 05 | [InsightEngine 深度洞察引擎](./05-深度洞察引擎InsightEngine/README.md) | 数据库挖掘、聚类分析、情感分析 | agent.py 41KB |
| 06 | [ReportEngine 报告引擎](./06-报告引擎ReportEngine/README.md) | 模板系统、IR中间表示、HTML/PDF渲染 | agent.py 66KB |
| 07 | [ForumEngine 论坛引擎](./07-论坛引擎ForumEngine/README.md) | Agent协作机制、主持人引导、辩论流程 | monitor.py 39KB |
| 08 | [MindSpider 爬虫系统](./08-爬虫系统MindSpider/README.md) | 社交平台数据采集、话题提取 | main.py 23KB |
| 09 | [情感分析模型](./09-情感分析模型/README.md) | 5种情感/主题模型选型与集成 | - |
| 10 | [配置与部署](./10-配置与部署/README.md) | 环境要求、API Key、Docker部署 | - |
| 11 | [单引擎独立应用](./11-单引擎独立应用/README.md) | Streamlit独立测试工具 | 各~10KB |

## 系统核心设计理念

1. **多智能体并行**：3个专业Agent同时工作，各自独立搜索分析
2. **论坛式协作**：Agent不是简单汇总，而是通过"论坛"辩论和碰撞
3. **内容与渲染分离**：IR中间表示让报告内容与渲染格式解耦
4. **模块化可扩展**：每个引擎独立，可替换模型和工具
5. **轻量化部署**：纯Python + Docker，一键部署

## 作者推荐的学习路径

```
1. 先看 01-系统架构概览 → 建立整体认知
2. 再看 02-Flask主应用 → 理解系统入口
3. 逐个看 03/04/05 → 理解三大分析引擎
4. 看 07-论坛引擎 → 理解协作机制
5. 看 06-报告引擎 → 理解报告生成
6. 看 08/09 → 理解数据采集层
7. 最后看 10-配置部署 → 动手运行
```
