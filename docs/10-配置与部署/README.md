# 配置与部署指南

## 环境要求

- **Python**: 3.10+
- **数据库**: MySQL 8.0+ 或 PostgreSQL 14+
- **Docker**（可选，推荐）
- **GPU**（可选，用于本地情感模型推理）

## 安装步骤

### 1. 克隆项目
```bash
git clone https://github.com/666ghj/BettaFish.git
cd BettaFish
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入所有 API Key 和数据库信息
```

### 4. 初始化数据库
```bash
# 创建数据库（MySQL）
mysql -u root -p -e "CREATE DATABASE bettafish CHARACTER SET utf8mb4;"

# 运行数据库迁移
python MindSpider/main.py --init-db
```

### 5. 启动系统
```bash
# 方式一：直接启动
python app.py

# 方式二：Docker 部署
docker-compose up -d
```

## API Key 清单

系统需要配置多个 LLM 的 API Key，每个引擎使用不同的模型：

| 引擎 | 推荐模型 | API 申请地址 | 用途 |
|------|---------|-------------|------|
| Insight | Kimi K2 | https://platform.moonshot.cn/ | 数据库深度分析 |
| Media | Gemini 2.5 Pro | https://aihubmix.com/ | 多模态理解 |
| Query | DeepSeek Chat | https://platform.deepseek.com/ | 网页搜索 |
| Report | Gemini 2.5 Pro | https://aihubmix.com/ | 报告生成 |
| MindSpider | DeepSeek | https://platform.deepseek.com/ | 爬虫决策 |
| ForumHost | Qwen3 | https://cloud.siliconflow.cn/ | 论坛主持 |

额外服务：
| 服务 | 用途 | 申请地址 |
|------|------|---------|
| Tavily | 网络搜索 | https://www.tavily.com/ |
| BochaAPI | AI搜索 | https://open.bochaai.com/ |
| AnspireAPI | AI搜索 | https://open.anspire.cn/ |

## Docker 部署

### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

### docker-compose.yml
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
    env_file: .env
    depends_on:
      - db
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}
      MYSQL_DATABASE: ${DB_NAME}
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

## 环境变量参考 (.env)

```ini
# Flask 服务器
HOST=0.0.0.0
PORT=5000

# 数据库
DB_DIALECT=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=bettafish

# Insight Agent（推荐Kimi）
INSIGHT_ENGINE_API_KEY=sk-xxx
INSIGHT_ENGINE_BASE_URL=https://api.moonshot.cn/v1
INSIGHT_ENGINE_MODEL_NAME=kimi-k2-0711-preview

# Media Agent（推荐Gemini）
MEDIA_ENGINE_API_KEY=sk-xxx
MEDIA_ENGINE_BASE_URL=https://aihubmix.com/v1
MEDIA_ENGINE_MODEL_NAME=gemini-2.5-pro

# Query Agent（推荐DeepSeek）
QUERY_ENGINE_API_KEY=sk-xxx
QUERY_ENGINE_BASE_URL=https://api.deepseek.com
QUERY_ENGINE_MODEL_NAME=deepseek-chat

# Report Agent（推荐Gemini）
REPORT_ENGINE_API_KEY=sk-xxx

# Forum Host（推荐Qwen3）
FORUM_HOST_API_KEY=sk-xxx

# 搜索工具
TAVILY_API_KEY=tvly-xxx
SEARCH_TOOL_TYPE=AnspireAPI
ANSPIRE_API_KEY=sk-xxx
```

## 目录结构说明

| 目录/文件 | 说明 |
|-----------|------|
| `logs/` | 运行日志（insight.log, media.log, query.log, forum.log） |
| `final_reports/` | 最终生成的报告文件（HTML） |
| `insight_engine_streamlit_reports/` | InsightEngine Streamlit 报告 |
| `media_engine_streamlit_reports/` | MediaEngine Streamlit 报告 |
| `query_engine_streamlit_reports/` | QueryEngine Streamlit 报告 |
| `static/` | 静态资源 |
| `.env` | 环境变量配置 |

## 测试

```bash
# 运行测试
python -m pytest tests/

# 论坛引擎测试
python -m pytest tests/test_monitor.py

# 报告引擎测试
python -m pytest tests/test_report_engine_sanitization.py
```
