# Account Risk Early Warning System

基于深度学习的社交媒体账号被盗风险预警系统。

## 系统概述

本系统采用 LSTM 神经网络检测异常行为模式，实时计算风险评分（0-100分），当风险分超过阈值时触发多渠道预警（短信、邮件、App推送）。

## 技术栈

- **Python 3.11** - 主要开发语言
- **FastAPI** - 异步 Web 框架
- **PyTorch** - 深度学习框架
- **PostgreSQL** - 关系型数据库
- **Redis** - 缓存和实时数据
- **ClickHouse** - 时序数据分析
- **Celery** - 分布式任务队列
- **Kafka** - 消息队列

## 功能特性

1. **用户行为特征采集**
   - 登录时间序列
   - IP 地理位置
   - 设备指纹
   - 操作行为序列

2. **LSTM 异常检测**
   - 双层 LSTM 神经网络
   - 实时推理服务
   - 模型版本管理

3. **风险评分引擎**
   - 多因子加权模型
   - 可配置阈值
   - 实时评分缓存

4. **多渠道预警**
   - 短信通知
   - 邮件通知
   - App 推送

## 项目结构

```
account_risk_system/
├── app/
│   ├── api/              # API 路由和端点
│   │   └── v1/
│   │       ├── endpoints/
│   │       └── middleware/
│   ├── core/             # 核心配置和安全
│   │   ├── config/
│   │   └── security/
│   ├── models/           # 数据模型
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # 业务逻辑服务
│   ├── ml/               # 机器学习模块
│   │   ├── models/       # LSTM 模型定义
│   │   ├── inference/    # 模型推理服务
│   │   └── training/     # 模型训练
│   ├── database/         # 数据库连接
│   ├── notifications/   # 通知服务
│   │   ├── channels/    # 通知渠道
│   │   └── templates/   # 通知模板
│   ├── tasks/           # Celery 任务
│   └── utils/           # 工具函数
├── config/               # 配置文件
├── docker/               # Docker 配置
├── scripts/             # 脚本工具
├── tests/               # 测试代码
└── data/                # 数据目录
    ├── raw/             # 原始数据
    ├── processed/      # 处理后数据
    └── models/          # 模型文件
```

## 快速开始

### 前置要求

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Kafka 3.0+

### 安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置

```bash
# 复制环境配置
cp config/settings.example.yaml config/settings.yaml
# 编辑配置文件
```

### 运行

```bash
# 启动 FastAPI 服务
uvicorn app.main:app --reload

# 启动 Celery Worker
celery -A app.tasks worker --loglevel=info

# 启动 Celery Beat
celery -A app.tasks beat --loglevel=info
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 开发

### 代码规范

```bash
# 运行 linter
ruff check app/

# 运行 type checker
mypy app/

# 运行 tests
pytest
```

### Docker 部署

```bash
# 构建镜像
docker build -t account-risk-system .

# 运行容器
docker-compose up -d
```

## 许可证

MIT License
