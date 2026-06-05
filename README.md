# APP_AI
以下是为您的项目编写的 `README.md`，涵盖了项目简介、功能、快速开始、配置说明、API 文档、部署指引等内容。

```markdown
# AI 资讯解读服务

基于大语言模型（LLM）的大宗商品资讯自动解读服务。接收资讯中台的新闻信号，调用 LLM 生成结构化解读和日报综述，并通过 HTTP 或 RabbitMQ 对外提供结果查询。

## 核心功能

- **单篇解读**：根据内容类型（价格、基本面、期货、分析等）使用不同提示词，生成事实性摘要，禁止投资建议。
- **多篇汇总**：定时对同一品目、同一天的已完成解读进行整合，生成日报综述。
- **双通道输入**：支持 HTTP 内部接口（备用）和 RabbitMQ 队列消费（主通道）。
- **结果通知**：处理完成后将状态发送至 RabbitMQ 结果队列。
- **查询接口**：提供 REST API 查询单篇解读结果和每日汇总结果。

## 技术栈

- **Web 框架**：FastAPI + Uvicorn
- **LLM 调用**：Requests + Tenacity（重试）
- **数据库**：SQLite（开发）/ PostgreSQL（生产）
- **消息队列**：RabbitMQ（pika）
- **内容清洗**：BeautifulSoup4 + 正则
- **部署**：systemd + Nginx + Docker（可选）

## 快速开始

### 环境要求

- Python 3.9+
- RabbitMQ 服务
- LLM 服务（支持 OpenAI 兼容 API，如 vLLM 部署的 Qwen）
- PostgreSQL（生产环境推荐）

### 安装依赖

```bash
git clone <your-repo>
cd APP_AI_1
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 配置环境变量

复制 `.env.example` 为 `.env` 并修改：

```ini
# LLM 配置
LLM_URL=http://your-llm-server:8000/v1/chat/completions
LLM_API_KEY=your-api-key
LLM_MODEL=Qwen/Qwen3.5-35B-A3B
LLM_ENABLE_THINKING=false

# CMS 接口（资讯中台）
CMS_BASE_URL=http://mtdservice.sci99.com/info_v2
CMS_INFO_API_URL=https://oaapi.sci99.com/dmapi/ds/mtd/infoitem/search

# RabbitMQ
MQ_HOST=192.168.7.191
MQ_PORT=5672
MQ_USERNAME=guest
MQ_PASSWORD=guest
MQ_VHOST=CMS
MQ_SIGNAL_QUEUE=q_sci_news_enhance_ai_summary
MQ_RESULT_QUEUE=q_sci_news_enhance_ai_summary_result

# 数据库（开发用 SQLite，生产用 PostgreSQL）
DATABASE_URL=sqlite:///./data.db?check_same_thread=false&timeout=30

# 并发与定时
MQ_CONSUMER_THREADS=3
SUMMARY_INTERVAL_MINUTES=60
SUMMARY_CONCURRENT_WORKERS=3
```

### 初始化数据库

```bash
python -c "from app_ai.database import init_db; init_db()"
```

### 运行服务

开发环境：

```bash
uvicorn app_ai.main:app --reload --host 0.0.0.0 --port 8000
```

生产环境（使用 systemd 或 Docker，见下文）。

## API 文档

启动服务后访问 `http://localhost:8000/docs` 查看自动生成的交互式 API 文档。

### 内部信号接收（备用）

- **URL**：`POST /internal/newsid`
- **请求体**：
  ```json
  {
    "news_id": "123456",
    "content_type": "price_info",
    "publish_date": "2024-12-10",
    "product_id": 101,
    "product_name": "螺纹钢"
  }
  ```
- **响应**：`{"status": "accepted", "news_id": "123456"}`

### 查询单篇解读

- **URL**：`GET /query/single?news_id=123456`
- **响应**：
  ```json
  {
    "news_id": "123456",
    "title": "...",
    "interpretation": "...",
    "status": "completed"
    
  }
  ```

### 查询日报汇总

- **URL**：`GET /query/summary?product_id=101&date=2024-12-10`
- **响应**：
  ```json
  {
    "product_id": 101,
    "product_name": "螺纹钢",
    "date": "2024-12-10",
    "summary_text": "...",
    "article_count": 15,
    "status": "completed"
  }
  ```

### 健康检查

- **URL**：`GET /health`
- **响应**：`{"status": "healthy", "llm": true, "database": true}`

## 部署到生产服务器

### 使用 systemd（推荐）

1. 将代码克隆到 `/opt/ai_interpret`
2. 创建虚拟环境并安装依赖
3. 配置 `.env` 文件（使用 PostgreSQL 和真实 MQ 地址）
4. 创建两个 systemd 服务文件：

**`/etc/systemd/system/fastapi-app.service`**

```ini
[Unit]
Description=AI Interpret API
After=network.target postgresql.service rabbitmq-server.service

[Service]
User=your_user
WorkingDirectory=/opt/ai_interpret
ExecStart=/opt/ai_interpret/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker -w 4 app_ai.main:app --bind 127.0.0.1:8000
Restart=always
RestartSec=10
EnvironmentFile=/opt/ai_interpret/.env

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/fastapi-worker.service`**

```ini
[Unit]
Description=AI Interpret Worker
After=network.target postgresql.service rabbitmq-server.service

[Service]
User=your_user
WorkingDirectory=/opt/ai_interpret
ExecStart=/opt/ai_interpret/venv/bin/python -m app_ai.worker
Restart=always
RestartSec=10
EnvironmentFile=/opt/ai_interpret/.env

[Install]
WantedBy=multi-user.target
```

5. 启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable fastapi-app fastapi-worker
sudo systemctl start fastapi-app fastapi-worker
```

### 使用 Docker（备选）

项目未自带 Dockerfile，可参考以下最小示例：

**Dockerfile**

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app_ai.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

使用 `docker-compose` 编排 app + postgres + rabbitmq。

## 性能建议

- **数据库**：生产环境必须使用 PostgreSQL，避免 SQLite 写锁瓶颈。
- **并发数**：根据 LLM 服务能力调整 `MQ_CONSUMER_THREADS`（推荐 3~6）。每日 2 万篇分散处理，3~4 个消费者即可。
- **缓存**：品目列表缓存 1 小时，减少 CMS 接口调用。
- **监控**：关注 RabbitMQ 队列堆积、LLM 调用耗时、数据库连接池状态。

## 常见问题

**1. 为什么关闭不了思考模式？**  
确保请求体中 `chat_template_kwargs` 在顶层，而非包裹在 `extra_body` 中。详见 `llm_service.py` 修改。

**2. 汇总提示“未找到”？**  
检查汇总是否已执行（默认每小时一次），确认数据库中对应 `product_id` 和 `date` 存在 `status='completed'` 的记录。

**3. SQLite 出现 `database is locked`？**  
切换到 PostgreSQL。若暂时无法切换，启用 WAL 模式并减少消费者线程数。

## 目录结构

```
app_ai/
├── api_internal.py       # 内部信号接口
├── api_query.py          # 查询接口
├── cms_service.py        # 资讯中台 API 客户端
├── config.py             # 配置管理
├── content_cleaner.py    # HTML 转纯文本
├── database.py           # 数据库模型
├── interpret_service.py  # 单篇解读核心
├── llm_service.py        # LLM 调用封装
├── logging_config.py     # 日志配置
├── main.py               # FastAPI 入口
├── models.py             # Pydantic 模型
├── mq_service.py         # RabbitMQ 客户端
├── prompts.py            # 提示词模板
├── safety.py             # 内容过滤 + 免责声明
├── summary_service.py    # 日报汇总
└── worker.py             # 后台消费者线程
```

## 许可证

内部项目，仅供公司内部使用。

## 维护者

[你的名字/团队]
```

你可以根据实际信息修改仓库地址、维护者等占位内容。