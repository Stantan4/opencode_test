## 上下文管理规则

### Token使用规范

1. **主动提示**: 每次回复后，如果 token 使用超过 50%，主动提示用户进行总结。
2. **状态文件优先**: 优先使用读写 `context.md` 的方式同步状态，避免在对话中重复长文本。

### 代码展示规范

1. **聚焦核心**: 回答涉及代码实现时，只展示核心代码块，不要重复输出未修改的整个文件。
2. **引用已有**: 如需修改现有代码，先读取文件，再展示差异部分。

### 任务管理规范

1. **任务启动前**: 读取 `context.md` 了解当前状态和TODO列表
2. **任务完成后**: 更新 `context.md` 记录完成项和待处理项
3. **保持简洁**: 避免在对话中重复已记录的状态信息

### 上下文续接规则

1. **继续工作**: 如果需要继续之前未完成的任务，先读取 `context.md` 确认进度
2. **新任务**: 每次新任务开始前，检查是否有未完成的遗留任务

---

## 项目规范

### 项目信息

- **项目名称**: Account Risk Early Warning System
- **项目用途**: 基于LSTM深度学习的社交媒体账号被盗风险预警系统，实时采集用户行为数据，检测异常登录和操作模式，提供风险评分和多渠道预警

### 技术栈

- **后端框架**: Python 3.11 + FastAPI 0.135+
- **深度学习**: PyTorch 2.11+ (LSTM模型)
- **数据库**: PostgreSQL (主数据) + Redis (缓存/实时数据) + ClickHouse (日志分析)
- **任务队列**: Celery + Kafka
- **测试**: pytest + pytest-asyncio
- **部署**: Docker + Docker Compose

---

## 编码规范

### 代码格式化

1. **格式化工具**: 必须使用 Black 进行代码格式化
2. **配置**: 项目根目录已配置 `pyproject.toml` 中的 Black 选项
3. **执行**: 提交代码前运行 `black .` 确保符合规范

### 类型注解

1. **必须标注**: 所有函数参数和返回值必须添加类型注解
2. **避免**: 禁止使用 `Any` 除非确有必要
3. **示例**:

```python
# ✅ 正确
def calculate_risk_score(user_id: str, features: list[float]) -> float:
    pass

# ❌ 错误
def calculate_risk_score(user_id, features):
    pass
```

### 文档字符串

1. **必须包含**: 所有公开类、函数必须添加 docstring
2. **格式**: 使用 Google 风格 docstring
3. **示例**:

```python
def predict_anomaly(sequence: torch.Tensor) -> torch.Tensor:
    """预测输入序列的异常分数。

    Args:
        sequence: 形状为 (batch, seq_len, features) 的输入张量

    Returns:
        形状为 (batch,) 的异常分数张量
    """
    pass
```

---

## 安全要求

### API 鉴权

1. **默认鉴权**: 所有 API 接口默认需要鉴权，除非明确标注 `@public_endpoint`
2. **JWT 验证**: 使用 `Depends(get_current_active_user)` 装饰器
3. **禁止绕过**: 禁止在生产环境关闭鉴权进行调试

### 敏感数据处理

1. **密码加密**: 用户密码必须使用 bcrypt 哈希存储，禁止明文
2. **Token 加密**: JWT secret 必须从环境变量读取
3. **敏感日志**: 禁止在日志中输出密码、Token、密钥等敏感信息
4. **数据库加密**: 敏感字段在数据库中加密存储 (如手机号、邮箱)

---

## 模型训练要求

### 模型序列化

1. **必须可保存**: 所有模型必须实现 `save()` 和 `load()` 方法
2. **格式**: 使用 PyTorch 的 `torch.save()` / `torch.load()`
3. **路径**: 模型文件保存在 `models/` 目录，版本号命名
4. **示例**:

```python
class LSTMAnomalyDetector(nn.Module):
    def save(self, path: str) -> None:
        """保存模型到指定路径"""
        torch.save(self.state_dict(), path)

    @classmethod
    def load(cls, path: str) -> "LSTMAnomalyDetector":
        """从指定路径加载模型"""
        model = cls()
        model.load_state_dict(torch.load(path))
        return model
```

### 模型版本管理

1. **版本号**: 每次训练更新版本号 (如 `lstm_v1.0.pth`)
2. **元数据**: 保存训练参数、数据集信息、评估指标
